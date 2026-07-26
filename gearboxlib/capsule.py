"""Construcción de la cápsula de telemetría minimizada ("presurizada").

Flujo (§3 de la misión):

    SQLite local → selección de elegibles → eliminación de identificadores →
    generalización y bucketing → escaneo de secretos → validación de schema →
    vista previa → consentimiento → JSON canónico → gzip → SHA-256 → cola

Decisión de diseño documentada: el ``contributor_id`` **no viaja dentro de la
cápsula**. La lista de "Datos permitidos" de §3 es exhaustiva y no lo incluye,
así que el seudónimo viaja en la cabecera HTTP ``X-Gearbox-Contributor``. Así el
cuerpo almacenado por el colector no contiene ningún identificador, ni siquiera
seudónimo, y la correlación queda confinada a la capa de transporte.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION
from .paths import gb_dir
from . import privacy

MAX_EVENTS_PER_CAPSULE = 500


def db_path() -> Path:
    return gb_dir() / "gearbox.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_marks (
            task_id TEXT PRIMARY KEY,
            capsule_id TEXT NOT NULL,
            marked_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    except sqlite3.Error:
        return set()


def eligible_rows(conn: sqlite3.Connection, limit: int = MAX_EVENTS_PER_CAPSULE) -> list[sqlite3.Row]:
    """Eventos con resultado conocido que aún no se han incluido en una cápsula.

    Sólo se seleccionan columnas de la allowlist: aunque la tabla local guarde
    más cosas, aquí no se leen. Es la primera barrera de minimización.
    """
    available = _columns(conn, "routing_events")
    if not available:
        return []
    wanted = [
        "task_id", "task_type", "gear", "model", "effort", "risk", "complexity",
        "ambiguity", "routing_confidence", "predicted_success", "outcome",
        "retrabajo", "cost_usd", "human_override", "feedback_reason", "rating",
        "latency_ms", "created_at",
    ]
    select = ", ".join(col for col in wanted if col in available)
    try:
        return list(conn.execute(
            f"""
            SELECT {select} FROM routing_events
            WHERE outcome IS NOT NULL
              AND task_id NOT IN (SELECT task_id FROM telemetry_marks)
            ORDER BY created_at ASC LIMIT ?
            """,
            (limit,),
        ))
    except sqlite3.Error:
        return []


def _get(row: sqlite3.Row, key: str, default: Any = None) -> Any:
    try:
        value = row[key]
    except (IndexError, KeyError):
        return default
    return default if value is None else value


def event_from_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convierte una fila local en un evento de cápsula. Sólo bandas y enums."""
    task_type = str(_get(row, "task_type", "unknown"))
    if task_type not in privacy.EVENT_FIELDS["task_type"]:
        task_type = "unknown"
    gear = str(_get(row, "gear", "G2"))
    if gear not in privacy.EVENT_FIELDS["predicted_gear"]:
        gear = "G2"
    effort = str(_get(row, "effort", "unknown"))
    if effort not in privacy.EVENT_FIELDS["effort"]:
        effort = "unknown"
    outcome = str(_get(row, "outcome", "unknown"))
    if outcome not in privacy.EVENT_FIELDS["outcome"]:
        outcome = "unknown"
    reason = str(_get(row, "feedback_reason", "none") or "none")
    if reason not in privacy.EVENT_FIELDS["feedback_reason"]:
        # `other_local_only` y cualquier valor desconocido se degradan a "none":
        # nunca se transmiten (§9).
        reason = "none"

    cost = _get(row, "cost_usd")
    latency = _get(row, "latency_ms")
    event = {
        "task_type": task_type,
        "predicted_gear": gear,
        "model_family": privacy.model_family(str(_get(row, "model", ""))),
        "effort": effort,
        "risk_band": privacy.level_band(_get(row, "risk")),
        "complexity_band": privacy.level_band(_get(row, "complexity")),
        "ambiguity_band": privacy.level_band(_get(row, "ambiguity")),
        "routing_confidence_band": privacy.probability_band(_get(row, "routing_confidence")),
        "predicted_success_band": privacy.probability_band(_get(row, "predicted_success")),
        "outcome": outcome,
        "rework": bool(_get(row, "retrabajo", 0)),
        "cost_band": _cost_band(cost),
        "latency_band": _latency_band(latency),
        "human_override": bool(_get(row, "human_override", 0)),
        "feedback_reason": reason,
    }
    rating = _get(row, "rating")
    if rating is not None:
        event["rating_band"] = privacy.rating_band(rating)
    return event


def _cost_band(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if number <= 0:
        return "unknown"
    for low, high in ((0, 0.05), (0.05, 0.25), (0.25, 1), (1, 5), (5, 20)):
        if low < number <= high:
            return f"{low}-{high}"
    return "20+"


def _latency_band(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if number <= 0:
        return "unknown"
    seconds = number / 1000.0
    for low, high in ((0, 5), (5, 30), (30, 120), (120, 600)):
        if low < seconds <= high:
            return f"{low}-{high}"
    return "600+"


def build(mode: str, *, period: str | None = None, limit: int = MAX_EVENTS_PER_CAPSULE,
          client_version: str = "3.0.0") -> tuple[dict[str, Any], list[str]]:
    """Construye la cápsula y devuelve (cápsula, task_ids incluidos).

    Los task_ids se devuelven **aparte**: sirven para marcar localmente lo ya
    enviado y jamás entran en el cuerpo.
    """
    with connect() as conn:
        rows = eligible_rows(conn, limit)
    events = [event_from_row(row) for row in rows]
    task_ids = [str(row["task_id"]) for row in rows]
    now = datetime.now(timezone.utc)
    capsule = {
        "schema_version": SCHEMA_VERSION,
        "client_version": client_version,
        "capsule_id": str(uuid.uuid4()),
        "generated_period": period or privacy.iso_week(now),
        "contribution_mode": mode,
        "events": events,
        "aggregate": {"event_count": len(events)},
    }
    return capsule, task_ids


def mark_sent(task_ids: list[str], capsule_id: str) -> int:
    if not task_ids:
        return 0
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with connect() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO telemetry_marks (task_id, capsule_id, marked_at) VALUES (?,?,?)",
            [(task_id, capsule_id, now) for task_id in task_ids],
        )
        conn.commit()
    return len(task_ids)


def clear_marks() -> int:
    with connect() as conn:
        cursor = conn.execute("DELETE FROM telemetry_marks")
        conn.commit()
        return cursor.rowcount or 0


def preview(capsule: dict[str, Any]) -> str:
    """Texto exacto de lo que saldría del equipo, más el veredicto del escáner."""
    import json

    body = json.dumps(capsule, ensure_ascii=False, indent=2, sort_keys=True)
    findings = privacy.scan_object(capsule)
    blockers = privacy.blocking(findings)
    lines = [
        "── CÁPSULA DE TELEMETRÍA (vista previa exacta) ──",
        body,
        "",
        f"Eventos: {capsule.get('aggregate', {}).get('event_count', 0)}",
        f"Periodo: {capsule.get('generated_period')} (semana, no hora exacta)",
        f"SHA-256 del cuerpo canónico: {privacy.sha256_hex(privacy.canonical_json(capsule))}",
    ]
    errors = privacy.validate_capsule(capsule)
    lines.append("Allowlist: " + ("✅ válida" if not errors else "❌ " + "; ".join(errors)))
    if blockers:
        lines.append("Escáner de privacidad: ❌ BLOQUEADO")
        lines.extend("  " + f.describe() for f in blockers)
    else:
        warnings = [f for f in findings if f.level == privacy.WARNING]
        lines.append("Escáner de privacidad: ✅ sin hallazgos que bloqueen"
                     + (f" ({len(warnings)} avisos)" if warnings else ""))
    return "\n".join(lines)
