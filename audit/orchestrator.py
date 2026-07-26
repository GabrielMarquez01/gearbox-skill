"""Orquestador de la auditoría. Aquí viven las reglas que no se negocian.

1. **Revisión ciega**: el auditor recibe la pregunta, los hechos, la
   jurisdicción, la fecha de corte y los criterios — nunca la respuesta del
   ejecutor, su conclusión ni su confianza. El código construye el prompt del
   auditor desde ``AuditRequest``, que no contiene la respuesta del ejecutor:
   filtrarla exigiría modificar esta clase, no olvidar un parámetro.
2. **Multi-vendor real**: sólo se declara ``cross_vendor`` si ejecutor y auditor
   pertenecen a **familias de proveedor distintas**. Un mismo vendor en ambos
   roles nunca cuenta, aunque sean modelos diferentes.
3. **L3 nunca se aprueba solo**: sin aprobación humana explícita el estado queda
   en ``needs_human``. No hay bandera que lo evite.
"""
from __future__ import annotations

from typing import Any, Callable

from . import compare, evidence
from .contracts import (AuditRequest, AuditResult, Capability, Level,
                        ProviderResponse, Role)
from .providers.base import Provider


class OrchestrationError(Exception):
    pass


def _blind_prompt(request: AuditRequest) -> str:
    """Prompt del auditor independiente. Se construye SOLO desde la petición."""
    return (
        request.as_prompt()
        + "\n\nEres un AUDITOR INDEPENDIENTE. No has visto ninguna respuesta previa. "
          "Responde por tu cuenta y señala explícitamente riesgos, omisiones y "
          "condiciones que invalidarían tu conclusión."
    )


def _executor_prompt(request: AuditRequest) -> str:
    return request.as_prompt() + "\n\nEres el EJECUTOR. Entrega la respuesta y su fundamento."


def run_audit(request: AuditRequest, executor: Provider, auditor: Provider | None = None,
              *, accessibility_checker: Callable[[str], bool] | None = None,
              routing_confidence: float = 0.0, timeout: int = 180) -> AuditResult:
    """Ejecuta la auditoría completa y devuelve un resultado sin aprobar."""
    level = request.level
    result = AuditResult(request=request, level=level, routing_confidence=routing_confidence)

    executor_response = executor.run(_executor_prompt(request), Role.EXECUTOR, timeout=timeout)
    result.executor = executor_response
    if not executor_response.ok:
        result.status = "needs_human"
        result.notes.append(f"el ejecutor no produjo resultado: {executor_response.error}")
        return result

    if auditor is None:
        result.status = "needs_human" if level != Level.L1 else "pending"
        result.notes.append(
            "sin auditor independiente: el resultado NO es multi-vendor y no puede "
            "declararse validado"
        )
        result.factual_confidence = evidence.factual_confidence(
            evidence.normalize_claims(executor_response.claims)
        )
        result.decision_readiness = _readiness(result)
        return result

    # ── revisión ciega: el prompt del auditor no deriva de la respuesta A ──
    auditor_response = auditor.run(_blind_prompt(request), Role.INDEPENDENT_AUDITOR,
                                   timeout=timeout)
    result.auditor = auditor_response
    if not auditor_response.ok:
        result.status = "needs_human"
        result.notes.append(f"el auditor no respondió ({auditor_response.error}): "
                            "no hay auditoría cruzada")
        result.factual_confidence = evidence.factual_confidence(
            evidence.normalize_claims(executor_response.claims)
        )
        result.decision_readiness = _readiness(result)
        return result

    result.cross_vendor, result.cross_vendor_reason = _cross_vendor(
        executor_response, auditor_response
    )

    # ── evidencia: normalizar, marcar obsoletas, verificar accesibilidad ──
    exec_claims = evidence.verify_accessibility(
        evidence.mark_stale(executor_response.claims), accessibility_checker)
    audit_claims = evidence.verify_accessibility(
        evidence.mark_stale(auditor_response.claims), accessibility_checker)
    exec_claims = evidence.normalize_claims(exec_claims)
    audit_claims = evidence.normalize_claims(audit_claims)
    executor_response.claims = tuple(exec_claims)
    auditor_response.claims = tuple(audit_claims)

    summary = compare.summarize(executor_response, auditor_response)
    result.agreements = summary["agreements"]
    result.discrepancies = summary["discrepancies"]
    result.omissions = summary["omissions"]

    result.factual_confidence = round(
        (evidence.factual_confidence(exec_claims) + evidence.factual_confidence(audit_claims)) / 2,
        3,
    )
    if summary["consensus_without_evidence"]:
        result.notes.append(
            "RIESGO: ambos coinciden pero ninguno aporta fuente primaria accedida. "
            "Coincidir no es validar."
        )
        result.factual_confidence = min(result.factual_confidence, 0.35)
    if summary["material_conflict"]:
        result.notes.append("conflicto material entre proveedores: exige revisión humana")
    if not result.cross_vendor:
        result.notes.append(
            f"NO es auditoría multi-vendor: {result.cross_vendor_reason}"
        )

    result.decision_readiness = _readiness(result)
    result.status = _status(result, summary)
    return result


def _cross_vendor(executor: ProviderResponse, auditor: ProviderResponse) -> tuple[bool, str]:
    if executor.vendor_family == auditor.vendor_family:
        return False, (f"ejecutor y auditor pertenecen a la misma familia "
                       f"('{executor.vendor_family}')")
    if executor.vendor_family in ("", "otro") or auditor.vendor_family in ("", "otro"):
        return False, "alguna familia de proveedor no está declarada"
    return True, (f"familias distintas: {executor.vendor_family} vs {auditor.vendor_family}")


def _readiness(result: AuditResult) -> float:
    """Disposición para ACTUAR. Es la más severa de las tres confianzas.

    No se promedia con optimismo: cada carencia estructural la recorta.
    """
    score = min(result.factual_confidence, 1.0)
    if not result.cross_vendor:
        score *= 0.6
    if result.discrepancies:
        score *= 0.6
    if result.level == Level.L3 and not result.human_approved:
        score = min(score, 0.5)
    if result.auditor is None:
        score *= 0.5
    return round(max(0.0, min(1.0, score)), 3)


def _status(result: AuditResult, summary: dict[str, Any]) -> str:
    if result.level == Level.L3:
        return "needs_human"
    if summary["material_conflict"] or not result.cross_vendor:
        return "needs_human"
    return "pending"


def approve(result: AuditResult, approver: str, *, accept: bool = True) -> AuditResult:
    """Aprobación humana explícita. Sin nombre de responsable no hay aprobación.

    Es el único camino para que un L3 quede ``approved``: no existe bandera de
    configuración, variable de entorno ni modo autónomo que lo sustituya.
    """
    if not approver or not approver.strip():
        raise OrchestrationError("la aprobación exige identificar a la persona responsable")
    result.human_approved = bool(accept)
    result.human_approver = approver.strip()
    result.status = "approved" if accept else "rejected"
    result.decision_readiness = _readiness(result)
    result.notes.append(
        f"{'aprobado' if accept else 'rechazado'} por {result.human_approver} "
        f"(nivel {result.level.value})"
    )
    return result


def capability_report(providers: list[Provider]) -> list[dict[str, str]]:
    return [
        {"name": p.name, "vendor_family": p.vendor_family, "capability": p.capability().value}
        for p in providers
    ]


def pick_pair(providers: list[Provider]) -> tuple[Provider, Provider | None]:
    """Elige ejecutor y auditor de familias distintas entre los disponibles."""
    usable = [p for p in providers if p.capability() == Capability.AVAILABLE]
    if not usable:
        raise OrchestrationError("no hay ningún proveedor disponible")
    executor = usable[0]
    auditor = next((p for p in usable[1:] if p.vendor_family != executor.vendor_family), None)
    return executor, auditor
