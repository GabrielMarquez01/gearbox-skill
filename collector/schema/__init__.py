"""Validación del lado servidor, **independiente** del cliente.

Deliberadamente no importa ``gearboxlib``: un colector no debe confiar en la
definición que trae quien envía. Si el cliente y el servidor divergen, el
servidor manda y el cliente recibe un rechazo estructurado.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).parent / "capsule-1.0.json"
SUPPORTED_SCHEMA_VERSIONS = ("1.0",)

CAPSULE_FIELDS = {"schema_version", "client_version", "capsule_id", "generated_period",
                  "contribution_mode", "events", "aggregate"}
AGGREGATE_FIELDS = {"event_count"}

ENUMS: dict[str, set[str]] = {
    "task_type": {"routine", "content", "implementation", "debugging", "planning",
                  "deep_analysis", "architecture", "critical", "research", "unknown"},
    "predicted_gear": {"G0", "G1", "G2", "G3", "G3.5", "G4", "G5"},
    "model_family": {"haiku", "sonnet", "opus", "opusplan", "fable", "other"},
    "effort": {"low", "medium", "high", "xhigh", "unknown"},
    "risk_band": {"low", "medium", "high"},
    "complexity_band": {"low", "medium", "high"},
    "ambiguity_band": {"low", "medium", "high"},
    "outcome": {"accepted", "rejected", "rework", "unknown"},
    "feedback_reason": {"wrong_gear", "wrong_model", "insufficient_depth", "excessive_cost",
                        "incorrect_result", "missing_source", "unnecessary_escalation",
                        "needed_human_review", "none"},
}
BOOLEANS = {"rework", "human_override"}
BANDS = {"routing_confidence_band", "predicted_success_band", "cost_band",
         "latency_band", "rating_band"}
EVENT_FIELDS = set(ENUMS) | BOOLEANS | BANDS

BAND_RE = re.compile(r"^(?:unknown|\d+(?:\.\d+)?-\d+(?:\.\d+)?|\d+\+)$")
PERIOD_RE = re.compile(r"^\d{4}-W\d{2}$|^\d{4}-\d{2}-\d{2}$")
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                     r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
VERSION_RE = re.compile(r"^\d+\.\d+(?:\.\d+)?(?:-[A-Za-z0-9.]+)?$")
MAX_EVENTS = 1000
MAX_STRING_LEN = 32


class SchemaError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors[:6]))


def normalize_version(value: Any) -> str:
    """Normaliza '3.0.0-preview.2' → '3.0'. Evita cardinalidad infinita en métricas."""
    text = str(value or "").strip()
    match = re.match(r"^(\d+)\.(\d+)", text)
    return f"{match.group(1)}.{match.group(2)}" if match else "unknown"


def validate(capsule: Any) -> dict[str, Any]:
    """Valida y devuelve la cápsula normalizada. Lanza SchemaError si no cumple."""
    errors: list[str] = []
    if not isinstance(capsule, dict):
        raise SchemaError(["el cuerpo debe ser un objeto JSON"])

    unknown = set(capsule) - CAPSULE_FIELDS
    if unknown:
        errors.append(f"campos no permitidos: {sorted(unknown)}")
    for required in CAPSULE_FIELDS:
        if required not in capsule:
            errors.append(f"falta {required}")

    if str(capsule.get("schema_version")) not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append("schema_version no soportada")
    if not VERSION_RE.match(str(capsule.get("client_version", ""))):
        errors.append("client_version con formato inválido")
    if not UUID_RE.match(str(capsule.get("capsule_id", ""))):
        errors.append("capsule_id debe ser UUID")
    if not PERIOD_RE.match(str(capsule.get("generated_period", ""))):
        errors.append("generated_period debe ser AAAA-Www o AAAA-MM-DD")
    if capsule.get("contribution_mode") not in ("community", "self-hosted"):
        errors.append("contribution_mode inválido")

    events = capsule.get("events")
    if not isinstance(events, list):
        errors.append("events debe ser lista")
        events = []
    elif len(events) > MAX_EVENTS:
        errors.append(f"demasiados eventos (>{MAX_EVENTS})")

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"events[{index}] no es objeto")
            continue
        unknown_ev = set(event) - EVENT_FIELDS
        if unknown_ev:
            errors.append(f"events[{index}]: campos no permitidos {sorted(unknown_ev)}")
        for key, value in event.items():
            if key in ENUMS and value not in ENUMS[key]:
                errors.append(f"events[{index}].{key} fuera del enum")
            elif key in BOOLEANS and not isinstance(value, bool):
                errors.append(f"events[{index}].{key} debe ser booleano")
            elif key in BANDS and (not isinstance(value, str) or not BAND_RE.match(value)):
                errors.append(f"events[{index}].{key} no es una banda válida")
            if isinstance(value, str) and len(value) > MAX_STRING_LEN:
                errors.append(f"events[{index}].{key}: cadena larga (texto libre no permitido)")

    aggregate = capsule.get("aggregate")
    if not isinstance(aggregate, dict):
        errors.append("aggregate debe ser objeto")
    else:
        if set(aggregate) - AGGREGATE_FIELDS:
            errors.append("aggregate: campos no permitidos")
        count = aggregate.get("event_count")
        if not isinstance(count, int) or isinstance(count, bool):
            errors.append("aggregate.event_count debe ser entero")
        elif count != len(events):
            errors.append("aggregate.event_count no coincide con events")

    if errors:
        raise SchemaError(errors)

    normalized = dict(capsule)
    normalized["client_version"] = normalize_version(capsule.get("client_version"))
    return normalized


def published_schema() -> dict[str, Any]:
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"error": "schema no disponible"}
