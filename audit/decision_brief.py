"""Decision Intelligence Brief — 19 secciones obligatorias (§12).

Objetivo doble y explícito: que una persona no técnica pueda decidir con él, y
que un especialista pueda auditarlo. Por eso jamás se publica un único número de
confianza: van los tres separados, con su significado en lenguaje llano.
"""
from __future__ import annotations

from typing import Any

from . import compare, evidence
from .contracts import AuditResult, ClaimType, Level

SECTIONS = (
    "Decisión que debe tomarse",
    "Respuesta ejecutiva",
    "Hechos confirmados",
    "Información faltante",
    "Supuestos",
    "Posición del ejecutor",
    "Posición del auditor independiente",
    "Coincidencias",
    "Discrepancias y omisiones",
    "Evidencia y jerarquía de fuentes",
    "Escenarios posibles",
    "Riesgo de cada escenario",
    "Recomendación razonada",
    "Confianza del routing",
    "Confianza factual",
    "Confianza para actuar",
    "Qué podría cambiar la conclusión",
    "Próxima acción",
    "Aprobación humana requerida",
)


def _claims_of(result: AuditResult, kind: ClaimType) -> list[str]:
    out: list[str] = []
    for response in (result.executor, result.auditor):
        if not response:
            continue
        for claim in response.claims:
            if claim.claim_type == kind:
                origin = response.provider
                out.append(f"({origin}) {claim.text.strip()}")
    return out


def _sources_table(result: AuditResult) -> list[str]:
    rows = ["| Nivel | Fuente | Jurisdicción | Publicada | ¿Verificada? | ¿Vigente? |",
            "|---|---|---|---|---|---|"]
    seen: set[str] = set()
    for response in (result.executor, result.auditor):
        if not response:
            continue
        for claim in response.claims:
            for source in claim.sources:
                if source.identifier in seen:
                    continue
                seen.add(source.identifier)
                rows.append(
                    f"| {source.tier.value} | {source.identifier[:80]} | "
                    f"{source.jurisdiction or '—'} | {source.published or '—'} | "
                    f"{'sí' if source.accessed else 'NO'} | "
                    f"{'no (marcada obsoleta)' if source.stale else 'sí'} |"
                )
    if len(rows) == 2:
        rows.append("| — | *ninguna fuente citada* | — | — | — | — |")
    return rows


def _scenarios(result: AuditResult) -> list[tuple[str, str, str]]:
    """Escenarios derivados del estado real de la evidencia (no inventados)."""
    scenarios: list[tuple[str, str, str]] = []
    if result.cross_vendor and not result.discrepancies and result.factual_confidence >= 0.6:
        scenarios.append((
            "La conclusión se sostiene",
            "Dos proveedores independientes coinciden y hay fuente primaria verificada.",
            "Bajo — el error residual sería una fuente mal interpretada por ambos.",
        ))
    if result.discrepancies:
        scenarios.append((
            "Uno de los dos está equivocado",
            "Hay discrepancias materiales sin resolver entre ejecutor y auditor.",
            "Alto — actuar ahora significa elegir a ciegas entre dos versiones.",
        ))
    if result.factual_confidence < 0.5:
        scenarios.append((
            "Ambos se apoyan en memoria, no en fuentes",
            "La confianza factual es baja: faltan fuentes primarias accedidas.",
            "Alto — una coincidencia sin evidencia puede ser un error compartido.",
        ))
    if not result.cross_vendor:
        scenarios.append((
            "Falta contraste real",
            "No hubo dos familias de proveedor distintas revisando el mismo problema.",
            "Medio a alto — no hay independencia que detecte un sesgo del modelo.",
        ))
    if not scenarios:
        scenarios.append((
            "Evidencia parcial",
            "No hay contradicción, pero tampoco respaldo suficiente para cerrar.",
            "Medio — conviene completar la evidencia antes de actuar.",
        ))
    return scenarios


def _readiness_words(value: float) -> str:
    if value >= 0.75:
        return "alta — la evidencia sostiene actuar"
    if value >= 0.5:
        return "media — se puede avanzar con condiciones y vigilancia"
    if value >= 0.25:
        return "baja — falta evidencia; actuar es apostar"
    return "muy baja — no hay base para actuar"


def render(result: AuditResult, *, decision: str = "") -> str:
    """Genera el brief en Markdown. Todas las secciones aparecen siempre.

    Si una sección no tiene contenido, se dice explícitamente. Un brief con
    huecos declarados es honesto; uno que omite secciones, no.
    """
    request = result.request
    facts = _claims_of(result, ClaimType.CONFIRMED_FACT)
    assumptions = _claims_of(result, ClaimType.ASSUMPTION)
    uncertainties = _claims_of(result, ClaimType.UNCERTAINTY)
    gaps: list[str] = []
    for response in (result.executor, result.auditor):
        if response:
            gaps.extend(evidence.missing_evidence(response.claims))

    lines: list[str] = ["# Decision Intelligence Brief", ""]

    def section(number: int, body: list[str]) -> None:
        lines.append(f"## {number}. {SECTIONS[number - 1]}")
        lines.extend(body or ["*(sin contenido: no se produjo información para esta sección)*"])
        lines.append("")

    section(1, [decision or request.question,
                "",
                f"- Nivel de auditoría exigido: **{result.level.value}**"
                + (" (dominio crítico)" if result.level == Level.L3 else ""),
                f"- Dominios declarados: {', '.join(request.domains) or 'ninguno'}",
                f"- Jurisdicción: {request.jurisdiction or 'no declarada'}",
                f"- Fecha de corte: {request.cutoff_date or 'no declarada'}"])

    executive = []
    if result.executor and result.executor.answer:
        executive.append(result.executor.answer.strip()[:800])
    executive.append("")
    executive.append(f"**Estado:** `{result.status}`  ·  **Auditoría multi-vendor:** "
                     f"{'sí' if result.cross_vendor else 'NO'} ({result.cross_vendor_reason})")
    section(2, executive)

    section(3, [f"- {f}" for f in facts] or
            ["*No hay hechos confirmados con fuente primaria verificada.*"])
    section(4, [f"- {g}" for g in dict.fromkeys(gaps)] or ["- Ninguna carencia detectada."])
    section(5, [f"- {a}" for a in assumptions] or ["- No se declararon supuestos explícitos."])

    section(6, _position(result.executor))
    section(7, _position(result.auditor) if result.auditor else
            ["*No hubo auditor independiente. La revisión cruzada no ocurrió.*"])

    section(8, [f"- {a}" for a in result.agreements] or ["- Sin coincidencias identificadas."])
    section(9, ([f"- ❗ {d}" for d in result.discrepancies]
                + [f"- ⚠ {o}" for o in result.omissions])
            or ["- Sin discrepancias ni omisiones detectadas."])
    section(10, _sources_table(result) + [
        "",
        "Regla aplicada: una fuente primaria (nivel A) vigente y verificada pesa más "
        "que varias secundarias. Toda afirmación marcada como *hecho confirmado* sin "
        "fuente primaria accedida fue degradada automáticamente a *inferencia*.",
    ])

    scenarios = _scenarios(result)
    section(11, [f"{i}. **{name}** — {why}" for i, (name, why, _) in enumerate(scenarios, 1)])
    section(12, [f"{i}. **{name}** — riesgo: {risk}"
                 for i, (name, _, risk) in enumerate(scenarios, 1)])

    section(13, _recommendation(result))

    section(14, [f"**{result.routing_confidence:.0%}** — qué tan seguro está Gearbox de haber "
                 "elegido la marcha y el motor correctos. No dice nada sobre si la "
                 "respuesta es verdadera."])
    section(15, [f"**{result.factual_confidence:.0%}** — qué tan sostenida por evidencia "
                 "verificable está la respuesta. Baja si se apoya en memoria del modelo."])
    section(16, [f"**{result.decision_readiness:.0%}** — {_readiness_words(result.decision_readiness)}.",
                 "",
                 "Estas tres confianzas son independientes a propósito: se puede rutear "
                 "perfecto y aun así no tener evidencia para decidir."])

    section(17, ([f"- {u}" for u in uncertainties] or []) + [
        "- Que aparezca una fuente primaria vigente que contradiga lo anterior.",
        "- Que cambie la jurisdicción o la fecha de corte aplicable.",
        "- Que un especialista humano identifique un supuesto inválido.",
    ])

    section(18, _next_action(result))

    section(19, _human_gate(result))

    lines.append("---")
    lines.append("")
    lines.append("*Este brief no sustituye asesoría profesional. En dominios críticos la "
                 "decisión final es de una persona responsable identificada.*")
    return "\n".join(lines)


def _position(response) -> list[str]:
    if not response:
        return ["*No disponible.*"]
    if not response.ok:
        return [f"*No produjo respuesta: {response.error} (estado: {response.capability.value})*"]
    body = [f"**Proveedor:** {response.provider} (familia `{response.vendor_family}`)",
            f"**Confianza declarada por el proveedor:** {response.confidence:.0%}",
            ""]
    body.append(response.answer.strip()[:1500] or "*(respuesta vacía)*")
    if response.truncated:
        body.append("\n*(salida truncada por límite de tamaño)*")
    return body


def _recommendation(result: AuditResult) -> list[str]:
    if result.status == "approved":
        return [f"Proceder según lo aprobado por **{result.human_approver}**.",
                "La aprobación humana quedó registrada; el alcance no puede ampliarse "
                "sin una nueva aprobación."]
    if result.discrepancies:
        return ["**No actuar todavía.** Resolver primero las discrepancias listadas en la "
                "sección 9, idealmente con la fuente primaria en mano.",
                "Si la decisión no puede esperar, documentar cuál versión se eligió y por qué."]
    if result.factual_confidence < 0.5:
        return ["**Completar evidencia antes de actuar.** La conclusión no está sostenida "
                "por fuentes primarias verificadas; hoy descansa en la memoria de los "
                "modelos, que no es una fuente."]
    if not result.cross_vendor:
        return ["**Obtener una segunda opinión de otra familia de proveedor** antes de "
                "tratar esto como verificado. Un solo vendor no es auditoría cruzada."]
    return ["Avanzar con las condiciones descritas, vigilando los supuestos de la sección 5."]


def _next_action(result: AuditResult) -> list[str]:
    if result.status == "needs_human":
        if result.level == Level.L3:
            return ["1. Entregar este brief al especialista responsable del dominio.",
                    "2. Registrar su aprobación o rechazo con nombre.",
                    "3. Sin ese paso, el trabajo NO puede marcarse como aprobado."]
        return ["1. Resolver el conflicto material o conseguir el segundo proveedor.",
                "2. Repetir la auditoría.",
                "3. Volver a evaluar la disposición para actuar."]
    if result.status == "approved":
        return ["Ejecutar dentro del alcance aprobado y conservar este brief como evidencia."]
    return ["Revisar las carencias de la sección 4 y decidir si se completan o se asume el riesgo."]


def _human_gate(result: AuditResult) -> list[str]:
    if result.level == Level.L3:
        if result.human_approved:
            return [f"**Sí, y fue otorgada** por `{result.human_approver}`.",
                    "Dominio crítico: la responsabilidad profesional es de esa persona."]
        return ["**SÍ — OBLIGATORIA Y PENDIENTE.**",
                "",
                "Este trabajo toca un dominio crítico (fiscal, legal, financiero, pagos, "
                "privacidad, datos personales, salud, seguridad, producción o eliminación "
                "irreversible). No puede marcarse como aprobado por ningún sistema "
                "automático, sin importar cuánta confianza reporte."]
    if result.status == "needs_human":
        return ["**Sí**, por conflicto material o por falta de auditoría cruzada real."]
    return ["No obligatoria por nivel, pero recomendable si la acción es difícil de revertir."]


def as_dict(result: AuditResult) -> dict[str, Any]:
    return {
        "brief_sections": list(SECTIONS),
        "result": result.as_dict(),
        "evidence_executor": evidence.summarize(result.executor.claims) if result.executor else None,
        "evidence_auditor": evidence.summarize(result.auditor.claims) if result.auditor else None,
        "comparison": (compare.summarize(result.executor, result.auditor)
                       if result.executor and result.auditor else None),
    }
