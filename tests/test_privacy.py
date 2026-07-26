"""Pruebas de privacidad: escáner de secretos, bandas y allowlist.

Todas las credenciales de estas pruebas son FICTICIAS.
"""
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from support import FAKE_SECRETS, IsolatedHome, load_core, sample_capsule

from gearboxlib import privacy


class SecretScannerTests(unittest.TestCase):
    def test_detects_every_fake_secret_as_blocking(self):
        for name, value in FAKE_SECRETS.items():
            with self.subTest(secret=name):
                findings = privacy.scan_text(f"valor: {value}", field="prueba")
                self.assertTrue(
                    privacy.blocking(findings),
                    f"el escáner no bloqueó un secreto de tipo {name}",
                )

    def test_finding_never_contains_the_secret_value(self):
        for name, value in FAKE_SECRETS.items():
            with self.subTest(secret=name):
                for finding in privacy.scan_text(value, field="campo"):
                    rendered = json.dumps(finding.as_dict()) + finding.describe()
                    self.assertNotIn(value, rendered)
                    # Ni siquiera un fragmento largo del secreto.
                    if len(value) > 12:
                        self.assertNotIn(value[:12], rendered)

    def test_reports_field_and_position_but_not_content(self):
        findings = privacy.scan_text(f"prefijo {FAKE_SECRETS['aws']}", field="events[0].x")
        blocking = privacy.blocking(findings)[0]
        self.assertEqual(blocking.field, "events[0].x")
        self.assertGreater(blocking.position, 0)
        self.assertIn("posición", blocking.describe())

    def test_high_entropy_string_is_blocked(self):
        findings = privacy.scan_text("k7Fq2Zx9Lm4Pw8Rt6Yv3Nb5Hj1Gd0Sa2Qe4Uc7Iо", field="x")
        self.assertTrue(privacy.blocking(findings))

    def test_ordinary_text_is_not_blocked(self):
        for benign in ("implementation", "G2", "0.7-0.8", "accepted", "low", "2026-W30"):
            with self.subTest(value=benign):
                self.assertFalse(privacy.blocking(privacy.scan_text(benign, field="x")))

    def test_luhn_valid_number_blocks_but_random_digits_only_warn(self):
        card = privacy.scan_text("4111111111111111", field="x")
        self.assertTrue(privacy.blocking(card))
        random_digits = privacy.scan_text("1234567890123", field="x")
        self.assertFalse(privacy.blocking(random_digits))

    def test_scan_object_walks_nested_structures(self):
        payload = {"a": {"b": [{"c": FAKE_SECRETS["email"]}]}}
        findings = privacy.blocking(privacy.scan_object(payload))
        self.assertTrue(findings)
        self.assertEqual(findings[0].field, "a.b[0].c")


class AllowlistTests(unittest.TestCase):
    def test_valid_capsule_passes(self):
        self.assertEqual(privacy.validate_capsule(sample_capsule()), [])

    def test_unknown_top_level_field_is_rejected(self):
        errors = privacy.validate_capsule(sample_capsule(extra="x"))
        self.assertTrue(any("no permitidos" in e for e in errors))

    def test_forbidden_fields_are_rejected_one_by_one(self):
        for field in ("prompt", "prompt_hash", "session_id", "cwd", "repo", "path",
                      "email", "hostname", "token", "matched_signals", "created_at"):
            with self.subTest(field=field):
                capsule = sample_capsule()
                capsule[field] = "cualquier cosa"
                self.assertTrue(privacy.validate_capsule(capsule))

    def test_event_with_free_text_is_rejected(self):
        capsule = sample_capsule()
        capsule["events"][0]["feedback_reason"] = "el usuario dijo que no le gustó nada"
        self.assertTrue(privacy.validate_capsule(capsule))

    def test_event_with_unknown_field_is_rejected(self):
        capsule = sample_capsule()
        capsule["events"][0]["prompt"] = "texto"
        errors = privacy.validate_capsule(capsule)
        self.assertTrue(any("prohibidos" in e or "no permitidos" in e for e in errors))

    def test_exact_timestamp_period_is_rejected(self):
        self.assertTrue(privacy.validate_capsule(
            sample_capsule(generated_period="2026-07-25T14:33:02Z")))

    def test_event_count_must_match(self):
        capsule = sample_capsule(aggregate={"event_count": 99})
        self.assertTrue(privacy.validate_capsule(capsule))

    def test_assert_safe_raises_on_injected_secret(self):
        capsule = sample_capsule()
        capsule["events"][0]["task_type"] = "routine"
        capsule["client_version"] = FAKE_SECRETS["github"]   # simula fuga por bug
        with self.assertRaises((privacy.PrivacyViolation, ValueError)):
            privacy.assert_safe(capsule)


class BandingTests(unittest.TestCase):
    def test_probability_band_never_leaks_exact_value(self):
        self.assertEqual(privacy.probability_band(0.7345), "0.7-0.8")
        self.assertEqual(privacy.probability_band(1.0), "0.9-1.0")
        self.assertEqual(privacy.probability_band(0.0), "0.0-0.1")
        self.assertEqual(privacy.probability_band("no numérico"), "unknown")

    def test_level_band_is_categorical(self):
        self.assertEqual(privacy.level_band(0.1), "low")
        self.assertEqual(privacy.level_band(0.5), "medium")
        self.assertEqual(privacy.level_band(0.9), "high")

    def test_sample_band_groups_counts(self):
        self.assertEqual(privacy.sample_band(120), "100-249")
        self.assertEqual(privacy.sample_band(5000), "1000+")

    def test_model_family_generalizes(self):
        self.assertEqual(privacy.model_family("Claude Sonnet 5"), "sonnet")
        self.assertEqual(privacy.model_family("modelo-desconocido"), "other")


class LocalStorageTests(IsolatedHome):
    """La base local no debe guardar rutas, sesiones ni hashes de prompt."""

    def test_record_prediction_stores_no_path_no_session_no_prompt_hash(self):
        core = load_core()
        secret_path = "/home/gabriel/cliente-confidencial/proyecto"
        route = core.classify("Implementa la feature")
        record = core.record_prediction(route, "Implementa la feature", "sesion-abc", secret_path)

        self.assertNotIn("prompt_hash", record)
        self.assertNotIn("session_id", record)
        self.assertNotIn("project_id", record)

        with core.db_connect() as conn:
            row = dict(conn.execute(
                "SELECT * FROM routing_events WHERE task_id=?", (record["task_id"],)
            ).fetchone())
        self.assertIsNone(row["project_id"])
        self.assertIsNone(row["session_id"])
        self.assertIsNone(row["prompt_hash"])
        self.assertTrue(row["project_ref"])
        self.assertNotIn("cliente-confidencial", json.dumps(row))

        raw_db = (self.home / "gearbox.db").read_bytes()
        self.assertNotIn(b"cliente-confidencial", raw_db)
        self.assertNotIn(b"sesion-abc", raw_db)

    def test_local_ref_is_not_correlatable_across_installs(self):
        ref_a = privacy.local_ref(b"sal-uno", "/home/x/proyecto")
        ref_b = privacy.local_ref(b"sal-dos", "/home/x/proyecto")
        self.assertNotEqual(ref_a, ref_b)

    def test_scrub_local_clears_legacy_rows(self):
        core = load_core()
        with core.db_connect() as conn:
            conn.execute(
                "INSERT INTO routing_events (task_id, created_at, session_id, project_id, "
                "prompt_hash, prompt_chars, task_type, gear, model, effort, risk, complexity, "
                "ambiguity, routing_confidence, predicted_success, human_gate, reason) "
                "VALUES ('viejo','2026-01-01','s','/home/u/x','abc123',10,'implementation',"
                "'G2','sonnet','high',0.1,0.1,0.1,0.5,0.5,0,'r')"
            )
            conn.commit()
        self.assertEqual(core.scrub_legacy_identifiers(), 1)
        with core.db_connect() as conn:
            row = dict(conn.execute("SELECT * FROM routing_events WHERE task_id='viejo'").fetchone())
        self.assertIsNone(row["project_id"])
        self.assertIsNone(row["prompt_hash"])

    def test_hook_output_contains_no_prompt_text(self):
        core = load_core()
        prompt = "mi contraseña de producción es hunter2 en /home/gabriel/prod"
        route = core.classify(prompt)
        record = core.record_prediction(route, prompt, "s", "/home/gabriel/prod")
        context = core.prediction_context(record, "observe")
        self.assertNotIn("hunter2", context)
        self.assertNotIn("/home/gabriel", context)


if __name__ == "__main__":
    unittest.main()
