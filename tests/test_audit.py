"""Auditoría multi-vendor: ceguera del auditor, independencia real y gate humano."""
from __future__ import annotations

import json
import unittest

from support import FAKE_SECRETS

from audit import compare, decision_brief, evidence, orchestrator
from audit.contracts import (AuditRequest, Capability, Claim, ClaimType, Level,
                             ProviderResponse, Role, Source, SourceTier)
from audit.providers.base import Provider, classify_source, parse_claims
from audit.providers.manual import ManualProvider


class SpyProvider(ManualProvider):
    """Guarda el prompt que recibió, para comprobar qué se le mostró."""

    def __init__(self, text: str, *, vendor_family: str, label: str):
        super().__init__(text, vendor_family=vendor_family, label=label)
        self.seen_prompts: list[str] = []

    def run(self, prompt: str, role: Role, *, timeout: int = 0) -> ProviderResponse:
        self.seen_prompts.append(prompt)
        return super().run(prompt, role, timeout=timeout)


ANSWER_A = (
    "hecho confirmado: el plazo de conservación debe ser el mínimo necesario, "
    "artículo 11 de la ley aplicable https://www.dof.gob.mx/nota_detalle.php\n"
    "supuesto: el colector opera bajo jurisdicción mexicana\n"
    "confianza: 80%"
)
ANSWER_B = (
    "inferencia: 90 días parece excesivo frente al principio de minimización\n"
    "incertidumbre: depende de si hay obligación contable de conservar\n"
    "confianza: 60%"
)


def request(domains=("privacidad",)) -> AuditRequest:
    return AuditRequest(
        question="¿Cuánto tiempo conservar las cápsulas crudas?",
        facts=("El colector agrega y borra la cruda tras agregar.",),
        jurisdiction="MX",
        cutoff_date="2026-07-01",
        acceptance_criteria=("Citar la norma aplicable",),
        domains=domains,
    )


class BlindReviewTests(unittest.TestCase):
    def test_auditor_never_sees_the_executor_answer(self):
        executor = SpyProvider(ANSWER_A, vendor_family="anthropic", label="claude")
        auditor = SpyProvider(ANSWER_B, vendor_family="openai", label="codex")
        orchestrator.run_audit(request(), executor, auditor)

        shown = auditor.seen_prompts[0]
        self.assertNotIn(ANSWER_A, shown)
        self.assertNotIn("80%", shown)                       # ni su confianza
        self.assertNotIn("hecho confirmado: el plazo", shown)
        self.assertNotIn("claude", shown.lower())            # ni quién respondió

    def test_auditor_receives_the_required_context(self):
        executor = SpyProvider(ANSWER_A, vendor_family="anthropic", label="claude")
        auditor = SpyProvider(ANSWER_B, vendor_family="openai", label="codex")
        orchestrator.run_audit(request(), executor, auditor)

        shown = auditor.seen_prompts[0]
        for required in ("¿Cuánto tiempo conservar", "El colector agrega",
                         "MX", "2026-07-01", "Citar la norma", "cita fuentes"):
            self.assertIn(required, shown)

    def test_blind_prompt_is_built_only_from_the_request(self):
        """La ceguera es estructural: el prompt del auditor no puede contener la
        respuesta A porque se construye desde AuditRequest, que no la tiene."""
        prompt = orchestrator._blind_prompt(request())
        self.assertNotIn(ANSWER_A, prompt)
        self.assertIn("AUDITOR INDEPENDIENTE", prompt)


class CrossVendorTests(unittest.TestCase):
    def test_two_families_count_as_cross_vendor(self):
        result = orchestrator.run_audit(
            request(),
            ManualProvider(ANSWER_A, vendor_family="anthropic", label="claude"),
            ManualProvider(ANSWER_B, vendor_family="openai", label="codex"))
        self.assertTrue(result.cross_vendor)

    def test_same_family_is_not_cross_vendor(self):
        result = orchestrator.run_audit(
            request(),
            ManualProvider(ANSWER_A, vendor_family="anthropic", label="claude-a"),
            ManualProvider(ANSWER_B, vendor_family="anthropic", label="claude-b"))
        self.assertFalse(result.cross_vendor)
        self.assertIn("misma familia", result.cross_vendor_reason)
        self.assertEqual(result.status, "needs_human")

    def test_single_provider_is_never_cross_vendor(self):
        result = orchestrator.run_audit(
            request(), ManualProvider(ANSWER_A, vendor_family="anthropic", label="claude"))
        self.assertFalse(result.cross_vendor)
        self.assertTrue(any("sin auditor" in n for n in result.notes))

    def test_undeclared_family_does_not_count(self):
        result = orchestrator.run_audit(
            request(),
            ManualProvider(ANSWER_A, vendor_family="otro", label="x"),
            ManualProvider(ANSWER_B, vendor_family="openai", label="codex"))
        self.assertFalse(result.cross_vendor)

    def test_pick_pair_selects_different_families(self):
        class A(Provider):
            name, vendor_family, binary = "a", "anthropic", ""

            def capability(self):
                return Capability.AVAILABLE

        class A2(A):
            name = "a2"

        class B(A):
            name, vendor_family = "b", "openai"

        executor, auditor = orchestrator.pick_pair([A(), A2(), B()])
        self.assertNotEqual(executor.vendor_family, auditor.vendor_family)


class HumanGateTests(unittest.TestCase):
    def test_l3_domains_force_level_three(self):
        for domain in ("fiscal", "legal", "pagos", "salud", "datos_personales",
                       "seguridad", "produccion", "eliminacion_irreversible"):
            with self.subTest(domain=domain):
                self.assertEqual(request((domain,)).level, Level.L3)

    def test_l3_never_reaches_approved_on_its_own(self):
        result = orchestrator.run_audit(
            request(("fiscal",)),
            ManualProvider(ANSWER_A, vendor_family="anthropic", label="claude"),
            ManualProvider(ANSWER_A, vendor_family="openai", label="codex"))
        self.assertEqual(result.status, "needs_human")
        self.assertFalse(result.human_approved)

    def test_approval_requires_a_named_person(self):
        result = orchestrator.run_audit(
            request(("fiscal",)),
            ManualProvider(ANSWER_A, vendor_family="anthropic", label="claude"),
            ManualProvider(ANSWER_B, vendor_family="openai", label="codex"))
        with self.assertRaises(orchestrator.OrchestrationError):
            orchestrator.approve(result, "")
        approved = orchestrator.approve(result, "Contador responsable")
        self.assertEqual(approved.status, "approved")
        self.assertIn("Contador responsable", approved.notes[-1])

    def test_readiness_is_capped_until_a_human_approves(self):
        result = orchestrator.run_audit(
            request(("legal",)),
            ManualProvider(ANSWER_A, vendor_family="anthropic", label="claude"),
            ManualProvider(ANSWER_A, vendor_family="openai", label="codex"))
        self.assertLessEqual(result.decision_readiness, 0.5)


class EvidenceTests(unittest.TestCase):
    def test_confirmed_fact_without_primary_source_is_downgraded(self):
        claim = Claim("algo", ClaimType.CONFIRMED_FACT, (), 0.9)
        normalized = evidence.normalize_claims([claim])[0]
        self.assertEqual(normalized.claim_type, ClaimType.INFERENCE)

    def test_unverified_source_does_not_count_as_verified(self):
        source = Source(SourceTier.A, "https://www.dof.gob.mx/x", accessed=False)
        claim = Claim("x", ClaimType.CONFIRMED_FACT, (source,))
        self.assertFalse(claim.has_primary_source)
        self.assertLess(evidence.evidence_score(claim), 0.5)

    def test_one_primary_outweighs_several_secondary(self):
        primary = Claim("x", ClaimType.CONFIRMED_FACT,
                        (Source(SourceTier.A, "ley 1", accessed=True),))
        secondary = Claim("y", ClaimType.CONFIRMED_FACT, tuple(
            Source(SourceTier.D, f"blog {i}", accessed=True) for i in range(5)))
        self.assertGreater(evidence.evidence_score(primary), evidence.evidence_score(secondary))

    def test_stale_source_loses_weight(self):
        fresh = Source(SourceTier.A, "ley", published="2026-01-01", accessed=True)
        stale = Source(SourceTier.A, "ley", published="2001-01-01", accessed=True)
        marked = evidence.mark_stale([Claim("x", ClaimType.CONFIRMED_FACT, (stale,))])[0]
        self.assertTrue(marked.sources[0].stale)
        self.assertGreater(evidence.source_weight(fresh),
                           evidence.source_weight(marked.sources[0]))

    def test_accessibility_is_never_assumed(self):
        claim = Claim("x", ClaimType.CONFIRMED_FACT,
                      (Source(SourceTier.A, "https://ejemplo.invalid/x"),))
        untouched = evidence.verify_accessibility([claim], None)[0]
        self.assertFalse(untouched.sources[0].accessed)
        verified = evidence.verify_accessibility([claim], lambda ident: True)[0]
        self.assertTrue(verified.sources[0].accessed)

    def test_missing_evidence_is_listed(self):
        claim = Claim("afirmación fuerte", ClaimType.CONFIRMED_FACT, ())
        self.assertTrue(evidence.missing_evidence([claim]))

    def test_official_domains_are_tier_a(self):
        self.assertEqual(classify_source("https://www.dof.gob.mx/x"), SourceTier.A)
        self.assertEqual(classify_source("https://eur-lex.europa.eu/y"), SourceTier.A)
        self.assertEqual(classify_source("https://blog.random.com/z"), SourceTier.D)


class ConsensusTests(unittest.TestCase):
    def test_agreement_without_primary_sources_is_flagged_as_risk(self):
        text = "inferencia: la respuesta correcta es cuarenta y dos según mi conocimiento"
        result = orchestrator.run_audit(
            request(),
            ManualProvider(text, vendor_family="anthropic", label="claude"),
            ManualProvider(text, vendor_family="openai", label="codex"))
        self.assertTrue(any("Coincidir no es validar" in n for n in result.notes))
        self.assertLessEqual(result.factual_confidence, 0.35)

    def test_material_conflict_requires_human(self):
        result = orchestrator.run_audit(
            request(("privacidad",)),
            ManualProvider("inferencia: conservar noventa dias es correcto",
                           vendor_family="anthropic", label="claude"),
            ManualProvider("inferencia: conservar noventa dias viola la minimizacion",
                           vendor_family="openai", label="codex"))
        self.assertEqual(result.status, "needs_human")

    def test_three_confidences_are_independent(self):
        result = orchestrator.run_audit(
            request(), ManualProvider(ANSWER_A, vendor_family="anthropic", label="claude"),
            ManualProvider(ANSWER_B, vendor_family="openai", label="codex"),
            routing_confidence=0.95)
        self.assertEqual(result.routing_confidence, 0.95)
        self.assertNotEqual(result.routing_confidence, result.factual_confidence)
        self.assertLessEqual(result.decision_readiness, result.factual_confidence)


class BriefTests(unittest.TestCase):
    def _brief(self, domains=("privacidad",)) -> str:
        result = orchestrator.run_audit(
            request(domains),
            ManualProvider(ANSWER_A, vendor_family="anthropic", label="claude"),
            ManualProvider(ANSWER_B, vendor_family="openai", label="codex"),
            routing_confidence=0.8)
        return decision_brief.render(result)

    def test_all_nineteen_sections_are_present(self):
        brief = self._brief()
        for index, title in enumerate(decision_brief.SECTIONS, 1):
            self.assertIn(f"## {index}. {title}", brief)

    def test_brief_separates_facts_assumptions_and_discrepancies(self):
        brief = self._brief()
        self.assertIn("Hechos confirmados", brief)
        self.assertIn("Supuestos", brief)
        self.assertIn("Discrepancias y omisiones", brief)
        self.assertIn("Escenarios posibles", brief)

    def test_brief_never_shows_a_single_confidence_number(self):
        brief = self._brief()
        self.assertIn("Confianza del routing", brief)
        self.assertIn("Confianza factual", brief)
        self.assertIn("Confianza para actuar", brief)

    def test_l3_brief_states_human_approval_is_pending(self):
        brief = self._brief(("fiscal",))
        self.assertIn("OBLIGATORIA Y PENDIENTE", brief)


class ProviderSafetyTests(unittest.TestCase):
    def test_unavailable_binary_is_reported_not_guessed(self):
        class Ghost(Provider):
            name, vendor_family, binary = "fantasma", "otro", "binario-que-no-existe-xyz"

        response = Ghost().run("hola", Role.EXECUTOR)
        self.assertEqual(response.capability, Capability.UNAVAILABLE)
        self.assertFalse(response.ok)

    def test_provider_env_excludes_credentials(self):
        import os

        os.environ["GEARBOX_TELEMETRY_TOKEN"] = "no-debe-viajar"
        try:
            env = Provider()._env()
            self.assertNotIn("GEARBOX_TELEMETRY_TOKEN", env)
            for key in env:
                self.assertNotIn("TOKEN", key.upper())
                self.assertNotIn("KEY", key.upper())
        finally:
            os.environ.pop("GEARBOX_TELEMETRY_TOKEN", None)

    def test_adapters_use_argument_lists_never_shell(self):
        from audit.providers import REGISTRY

        for name, cls in REGISTRY.items():
            with self.subTest(provider=name):
                provider = cls() if name != "manual" else cls("x")
                self.assertIsInstance(provider.args, tuple)

    def test_unmarked_answer_becomes_low_confidence_opinion(self):
        claims, confidence = parse_claims("Yo creo que sí, sin más.")
        self.assertEqual(claims[0].claim_type, ClaimType.TECHNICAL_OPINION)
        self.assertLess(confidence, 0.5)


class TelemetryIsolationTests(unittest.TestCase):
    def test_audit_answers_never_reach_a_telemetry_capsule(self):
        """Las respuestas completas de los proveedores no son campos de cápsula."""
        from gearboxlib import privacy

        result = orchestrator.run_audit(
            request(),
            ManualProvider(ANSWER_A + FAKE_SECRETS["email"], vendor_family="anthropic",
                           label="claude"),
            ManualProvider(ANSWER_B, vendor_family="openai", label="codex"))
        serialized = json.dumps(result.as_dict())
        self.assertNotIn(FAKE_SECRETS["email"], serialized)   # as_dict no lleva answer
        self.assertIn("answer_chars", serialized)             # sólo la longitud
        capsule_fields = privacy.CAPSULE_FIELDS | set(privacy.EVENT_FIELDS)
        self.assertNotIn("answer", capsule_fields)
        self.assertNotIn("brief", capsule_fields)


if __name__ == "__main__":
    unittest.main()
