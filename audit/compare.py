"""Comparación de dos respuestas independientes.

Se ejecuta SÓLO después de que ambos proveedores respondieron. Antes de eso, el
auditor no ve nada del ejecutor (§10, revisión ciega): el orquestador es quien
garantiza el orden; este módulo no tiene forma de filtrar información porque
recibe las dos respuestas ya cerradas.

Regla explícita: coincidir **no** es validar. Dos modelos pueden equivocarse
igual — por eso ``consensus_without_evidence`` se reporta como riesgo, no como
confirmación.
"""
from __future__ import annotations

import re
from typing import Any

from .contracts import Claim, ClaimType, ProviderResponse

STOPWORDS = frozenset("""
a al algo ante antes como con contra cual cuando de del desde donde dos el ella
ellos en entre era es esta este esto fue ha hay la las le lo los mas más me mi
mucho muy no nos o os otro para pero por que quien se ser si sin sobre su sus
también tanto te tiene todo tu un una uno y ya the of and or to in on for is are
be with this that it as at by from
""".split())


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-záéíóúñü0-9]{4,}", text.lower())
    return {w for w in words if w not in STOPWORDS}


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _claim_key(claim: Claim) -> set[str]:
    return tokens(claim.text)


def compare_claims(executor: list[Claim], auditor: list[Claim],
                   *, threshold: float = 0.34) -> dict[str, list[str]]:
    """Empareja afirmaciones por solapamiento léxico y clasifica el resultado."""
    agreements: list[str] = []
    discrepancies: list[str] = []
    omissions: list[str] = []

    matched_auditor: set[int] = set()
    for claim in executor:
        best_index, best_score = -1, 0.0
        for index, other in enumerate(auditor):
            if index in matched_auditor:
                continue
            key_a, key_b = _claim_key(claim), _claim_key(other)
            score = len(key_a & key_b) / len(key_a | key_b) if (key_a or key_b) else 0.0
            if score > best_score:
                best_index, best_score = index, score
        if best_index >= 0 and best_score >= threshold:
            matched_auditor.add(best_index)
            other = auditor[best_index]
            if other.claim_type == claim.claim_type:
                agreements.append(f"[{claim.claim_type.value}] {claim.text[:160]}")
            else:
                discrepancies.append(
                    f"misma afirmación con distinta naturaleza — ejecutor la llama "
                    f"'{claim.claim_type.value}' y el auditor '{other.claim_type.value}': "
                    f"{claim.text[:120]}"
                )
        else:
            omissions.append(f"el auditor no abordó: {claim.text[:160]}")

    for index, other in enumerate(auditor):
        if index not in matched_auditor:
            discrepancies.append(f"el auditor añade y el ejecutor omitió: {other.text[:160]}")

    return {"agreements": agreements, "discrepancies": discrepancies, "omissions": omissions}


def material_conflict(comparison: dict[str, list[str]], executor: ProviderResponse,
                      auditor: ProviderResponse) -> bool:
    """¿El desacuerdo obliga a revisión humana?

    Sí cuando: hay discrepancias sobre hechos, cuando el auditor aporta material
    que el ejecutor no vio, o cuando las respuestas apenas se parecen.
    """
    if comparison["discrepancies"]:
        return True
    if similarity(executor.answer, auditor.answer) < 0.15:
        return True
    return False


def consensus_without_evidence(executor: ProviderResponse, auditor: ProviderResponse) -> bool:
    """Coincidencia SIN fuentes primarias en ninguno de los dos.

    Es la trampa clásica del "dos modelos coinciden = verdad". Se detecta y se
    reporta como riesgo explícito en el brief.
    """
    both_agree = similarity(executor.answer, auditor.answer) >= 0.5
    primary = any(c.has_primary_source for c in list(executor.claims) + list(auditor.claims))
    return both_agree and not primary


def summarize(executor: ProviderResponse, auditor: ProviderResponse) -> dict[str, Any]:
    comparison = compare_claims(list(executor.claims), list(auditor.claims))
    return {
        **comparison,
        "answer_similarity": round(similarity(executor.answer, auditor.answer), 3),
        "material_conflict": material_conflict(comparison, executor, auditor),
        "consensus_without_evidence": consensus_without_evidence(executor, auditor),
        "types_executor": _type_counts(executor),
        "types_auditor": _type_counts(auditor),
    }


def _type_counts(response: ProviderResponse) -> dict[str, int]:
    counts: dict[str, int] = {}
    for claim in response.claims:
        counts[claim.claim_type.value] = counts.get(claim.claim_type.value, 0) + 1
    return counts


__all__ = ["compare_claims", "material_conflict", "consensus_without_evidence",
           "similarity", "summarize", "ClaimType"]
