"""Jerarquía de fuentes y confianza factual (§11).

Principios que el código hace cumplir:

* una fuente **primaria vigente y accedida** pesa más que varias secundarias;
* la memoria del modelo NO es fuente: una afirmación sin fuente no puede ser
  "hecho confirmado", se degrada a inferencia;
* una fuente no accedida no cuenta como verificada;
* una fuente marcada como desactualizada pierde casi todo su peso;
* conflicto material entre proveedores ⇒ revisión humana obligatoria.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Callable, Iterable

from .contracts import Claim, ClaimType, Source, SourceTier

# Peso por nivel. La brecha A↔D es deliberadamente grande: es el punto entero.
TIER_WEIGHT = {SourceTier.A: 1.0, SourceTier.B: 0.6, SourceTier.C: 0.35, SourceTier.D: 0.15}
NOT_ACCESSED_PENALTY = 0.4
STALE_PENALTY = 0.15


def source_weight(source: Source) -> float:
    weight = TIER_WEIGHT.get(source.tier, 0.15)
    if not source.accessed:
        weight *= NOT_ACCESSED_PENALTY
    if source.stale:
        weight *= STALE_PENALTY
    return weight


def evidence_score(claim: Claim) -> float:
    """Peso de evidencia de una afirmación, saturando: cinco fuentes D nunca
    alcanzan a una A vigente."""
    if not claim.sources:
        return 0.0
    best = max(source_weight(s) for s in claim.sources)
    extra = sum(sorted((source_weight(s) for s in claim.sources), reverse=True)[1:])
    return min(1.0, best + extra * 0.15)


def normalize_claims(claims: Iterable[Claim]) -> list[Claim]:
    """Degrada a inferencia todo "hecho confirmado" sin fuente primaria accedida.

    Ésta es la regla que impide que la memoria del modelo se disfrace de hecho.
    """
    normalized: list[Claim] = []
    for claim in claims:
        if claim.claim_type == ClaimType.CONFIRMED_FACT and not claim.has_primary_source:
            normalized.append(Claim(
                text=claim.text, claim_type=ClaimType.INFERENCE,
                sources=claim.sources, confidence=min(claim.confidence, 0.5),
            ))
        else:
            normalized.append(claim)
    return normalized


def mark_stale(claims: Iterable[Claim], *, cutoff_year: int | None = None) -> list[Claim]:
    """Marca fuentes publicadas antes del corte declarado."""
    cutoff_year = cutoff_year or (date.today().year - 3)
    out: list[Claim] = []
    for claim in claims:
        sources = []
        for source in claim.sources:
            year = _year(source.published)
            stale = source.stale or (year is not None and year < cutoff_year)
            sources.append(Source(source.tier, source.identifier, source.title,
                                  source.published, source.jurisdiction,
                                  source.accessed, stale))
        out.append(Claim(claim.text, claim.claim_type, tuple(sources), claim.confidence))
    return out


def _year(published: str) -> int | None:
    for token in (published or "").replace("/", "-").split("-"):
        if token.isdigit() and len(token) == 4:
            return int(token)
    return None


def verify_accessibility(claims: Iterable[Claim],
                         checker: Callable[[str], bool] | None = None) -> list[Claim]:
    """Marca ``accessed`` sólo si el verificador confirma que la fuente existe.

    Sin verificador NO se marca nada: no se presume acceso. El verificador se
    inyecta (red, caché, revisión humana) para que esta capa sea probable sin
    tocar internet.
    """
    if checker is None:
        return list(claims)
    out: list[Claim] = []
    for claim in claims:
        sources = tuple(
            Source(s.tier, s.identifier, s.title, s.published, s.jurisdiction,
                   bool(checker(s.identifier)), s.stale)
            for s in claim.sources
        )
        out.append(Claim(claim.text, claim.claim_type, sources, claim.confidence))
    return out


def factual_confidence(claims: Iterable[Claim]) -> float:
    """Confianza FACTUAL: qué tan sostenida por evidencia está la respuesta.

    Deliberadamente distinta de la confianza declarada por el modelo. Un modelo
    muy seguro sin fuentes primarias obtiene un número bajo aquí.
    """
    claims = list(claims)
    facts = [c for c in claims if c.claim_type in
             (ClaimType.CONFIRMED_FACT, ClaimType.INFERENCE)]
    if not facts:
        return 0.0
    return round(sum(evidence_score(c) for c in facts) / len(facts), 3)


def missing_evidence(claims: Iterable[Claim]) -> list[str]:
    gaps: list[str] = []
    for claim in claims:
        if claim.claim_type == ClaimType.CONFIRMED_FACT and not claim.has_primary_source:
            gaps.append(f"afirmación sin fuente primaria accedida: «{claim.text[:120]}»")
        for source in claim.sources:
            if not source.accessed:
                gaps.append(f"fuente citada pero no verificada: {source.identifier[:120]}")
            elif source.stale:
                gaps.append(f"fuente potencialmente desactualizada: {source.identifier[:120]}")
    return gaps[:20]


def summarize(claims: Iterable[Claim]) -> dict[str, Any]:
    claims = list(claims)
    by_type: dict[str, int] = {}
    for claim in claims:
        by_type[claim.claim_type.value] = by_type.get(claim.claim_type.value, 0) + 1
    tiers: dict[str, int] = {}
    for claim in claims:
        for source in claim.sources:
            tiers[source.tier.value] = tiers.get(source.tier.value, 0) + 1
    return {
        "claims": len(claims),
        "by_type": by_type,
        "sources_by_tier": tiers,
        "factual_confidence": factual_confidence(claims),
        "gaps": missing_evidence(claims),
    }
