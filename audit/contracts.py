"""Contratos de la auditoría multi-vendor. Sin dependencias de proveedor.

Todo lo que cruza la frontera entre orquestador, proveedores y síntesis pasa por
estas estructuras. Si un proveedor no puede llenarlas, no puede participar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Role(str, Enum):
    EXECUTOR = "executor"
    INDEPENDENT_AUDITOR = "independent_auditor"
    EVIDENCE_VERIFIER = "evidence_verifier"
    DECISION_SYNTHESIZER = "decision_synthesizer"
    HUMAN_APPROVER = "human_approver"


class Level(str, Enum):
    L1 = "L1"   # autoverificación
    L2 = "L2"   # dos vendors independientes
    L3 = "L3"   # dos vendors + fuentes oficiales + especialista humano


class Capability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNAUTHENTICATED = "unauthenticated"
    UNSUPPORTED = "unsupported"


class ClaimType(str, Enum):
    """Distinción obligatoria (§11). Mezclar estas categorías es el error que la
    auditoría existe para evitar."""

    CONFIRMED_FACT = "hecho_confirmado"
    INFERENCE = "inferencia"
    ASSUMPTION = "supuesto"
    TECHNICAL_OPINION = "opinion_tecnica"
    RECOMMENDATION = "recomendacion"
    UNCERTAINTY = "incertidumbre"


class SourceTier(str, Enum):
    A = "A"   # leyes, reguladores, documentación oficial, contratos
    B = "B"   # tribunales, organismos técnicos, universidades
    C = "C"   # especialistas reconocidos
    D = "D"   # fuentes secundarias


# Dominios que obligan a L3 (§10). La lista es conservadora a propósito.
L3_DOMAINS = frozenset({
    "fiscal", "legal", "financiero", "pagos", "privacidad", "datos_personales",
    "salud", "seguridad", "produccion", "eliminacion_irreversible",
})


@dataclass(frozen=True)
class Source:
    tier: SourceTier
    identifier: str            # URL, número de norma, expediente, DOI…
    title: str = ""
    published: str = ""        # fecha declarada por la fuente
    jurisdiction: str = ""
    accessed: bool = False     # ¿alguien la abrió de verdad?
    stale: bool = False        # marcada como desactualizada

    def as_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier.value, "identifier": self.identifier, "title": self.title,
            "published": self.published, "jurisdiction": self.jurisdiction,
            "accessed": self.accessed, "stale": self.stale,
        }


@dataclass(frozen=True)
class Claim:
    """Una afirmación con su tipo y sus fuentes. Sin tipo, no entra al brief."""

    text: str
    claim_type: ClaimType
    sources: tuple[Source, ...] = ()
    confidence: float = 0.5

    @property
    def has_primary_source(self) -> bool:
        return any(s.tier == SourceTier.A and s.accessed and not s.stale for s in self.sources)

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text, "type": self.claim_type.value,
            "confidence": round(self.confidence, 3),
            "sources": [s.as_dict() for s in self.sources],
        }


@dataclass(frozen=True)
class AuditRequest:
    """Lo que se le entrega a CADA proveedor. El auditor ciego recibe esto y
    nada más: ni la respuesta del ejecutor, ni su conclusión, ni su confianza."""

    question: str
    facts: tuple[str, ...] = ()
    jurisdiction: str = ""
    cutoff_date: str = ""
    acceptance_criteria: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    require_sources: bool = True

    @property
    def level(self) -> Level:
        if any(domain in L3_DOMAINS for domain in self.domains):
            return Level.L3
        return Level.L2

    def as_prompt(self) -> str:
        parts = [
            "Responde de forma independiente. No conoces ninguna otra respuesta a esta pregunta.",
            f"PREGUNTA: {self.question}",
        ]
        if self.facts:
            parts.append("HECHOS DADOS:\n" + "\n".join(f"- {f}" for f in self.facts))
        if self.jurisdiction:
            parts.append(f"JURISDICCIÓN: {self.jurisdiction}")
        if self.cutoff_date:
            parts.append(f"FECHA DE CORTE: {self.cutoff_date}")
        if self.acceptance_criteria:
            parts.append("CRITERIOS DE ACEPTACIÓN:\n"
                         + "\n".join(f"- {c}" for c in self.acceptance_criteria))
        if self.require_sources:
            parts.append(
                "OBLIGATORIO: cita fuentes verificables (norma, artículo, documento oficial "
                "o URL) para cada afirmación factual. Distingue explícitamente hecho "
                "confirmado, inferencia, supuesto y opinión. No uses tu memoria como fuente: "
                "si no puedes citar, decláralo como incertidumbre."
            )
        return "\n\n".join(parts)


@dataclass
class ProviderResponse:
    provider: str
    vendor_family: str          # anthropic | openai | google | human | otro
    role: Role
    answer: str = ""
    claims: tuple[Claim, ...] = ()
    confidence: float = 0.5
    error: str = ""
    capability: Capability = Capability.AVAILABLE
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return not self.error and self.capability == Capability.AVAILABLE

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider, "vendor_family": self.vendor_family,
            "role": self.role.value, "confidence": round(self.confidence, 3),
            "capability": self.capability.value, "error": self.error,
            "truncated": self.truncated,
            "claims": [c.as_dict() for c in self.claims],
            "answer_chars": len(self.answer),
        }


@dataclass
class AuditResult:
    request: AuditRequest
    level: Level
    executor: ProviderResponse | None = None
    auditor: ProviderResponse | None = None
    cross_vendor: bool = False
    cross_vendor_reason: str = ""
    agreements: list[str] = field(default_factory=list)
    discrepancies: list[str] = field(default_factory=list)
    omissions: list[str] = field(default_factory=list)
    routing_confidence: float = 0.0
    factual_confidence: float = 0.0
    decision_readiness: float = 0.0
    human_approved: bool = False
    human_approver: str = ""
    status: str = "pending"     # pending | needs_human | approved | rejected
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "cross_vendor": self.cross_vendor,
            "cross_vendor_reason": self.cross_vendor_reason,
            "executor": self.executor.as_dict() if self.executor else None,
            "auditor": self.auditor.as_dict() if self.auditor else None,
            "agreements": self.agreements,
            "discrepancies": self.discrepancies,
            "omissions": self.omissions,
            "routing_confidence": round(self.routing_confidence, 3),
            "factual_confidence": round(self.factual_confidence, 3),
            "decision_readiness": round(self.decision_readiness, 3),
            "human_approved": self.human_approved,
            "status": self.status,
            "notes": self.notes,
        }
