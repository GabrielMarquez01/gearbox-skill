"""Detección de secretos/PII, generalización a bandas y allowlist estricta.

Tres defensas independientes, en este orden:

1. **Allowlist**: la cápsula se CONSTRUYE campo por campo desde un catálogo
   cerrado de claves y enums. Nada que no esté en el catálogo puede entrar.
2. **Bandas**: los números se generalizan a rangos antes de salir del equipo,
   para que una cifra exacta no funcione como cuasi-identificador.
3. **Escáner**: inspección del JSON serializado como red de seguridad. Si algo
   se filtró por un error de programación, el envío se bloquea.

El escáner nunca imprime el valor detectado: sólo tipo, campo y posición
aproximada (§4 de la misión).
"""
from __future__ import annotations

import hmac
import json
import math
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Iterable

# ─────────────────────────────────────────────────────────────────────────────
# Niveles
# ─────────────────────────────────────────────────────────────────────────────
BLOCK = "block"
WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    """Hallazgo del escáner. NO contiene el valor detectado, a propósito."""

    kind: str
    level: str
    field: str
    position: int
    length: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "level": self.level,
            "field": self.field,
            "position_approx": self.position,
            "length": self.length,
        }

    def describe(self) -> str:
        return (
            f"[{self.level}] {self.kind} en campo '{self.field}' "
            f"(posición ≈{self.position}, longitud {self.length})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Patrones. El orden importa sólo para la legibilidad del reporte.
# ─────────────────────────────────────────────────────────────────────────────
PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|ANPA)[0-9A-Z]{16}\b"), BLOCK),
    ("aws_secret_key", re.compile(r"(?i)aws_?secret_?access_?key\s*[=:]\s*\S{20,}"), BLOCK),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), BLOCK),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), BLOCK),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{16,}"), BLOCK),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9\-_]{20,}"), BLOCK),
    # Una llave real de Google trae 35 caracteres tras "AIza"; el rango es más
    # amplio a propósito: es preferible bloquear un parecido que dejar salir uno.
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z\-_]{28,45}"), BLOCK),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), BLOCK),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{4,}"), BLOCK),
    ("bearer_header", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]{16,}"), BLOCK),
    ("authorization_header", re.compile(r"(?i)\bauthorization\s*[:=]\s*\S+"), BLOCK),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), BLOCK),
    ("generic_secret_assignment",
     re.compile(r"(?i)\b(?:api[_-]?key|secret|token|passwd|password|cookie)\b\s*[=:]\s*\S{8,}"), BLOCK),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), BLOCK),
    ("url", re.compile(r"\b(?:https?|ftp|ssh|git)://\S+"), BLOCK),
    ("windows_path", re.compile(r"\b[A-Za-z]:\\\\?[^\s\"']+|\\\\\\\\wsl[^\s\"']*|\\\\wsl\.localhost\\[^\s\"']+"), BLOCK),
    ("unix_path", re.compile(r"(?:^|[\s\"'(=])/(?:home|Users|var|etc|opt|srv|root|mnt|tmp|usr)/[^\s\"']*"), BLOCK),
    ("ipv4", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"), BLOCK),
    ("ipv6", re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){4,7}[0-9A-Fa-f]{1,4}\b"), BLOCK),
    ("uuid", re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"), BLOCK),
    ("phone", re.compile(r"(?:\+\d{1,3}[\s.\-]?)?(?:\(\d{2,4}\)[\s.\-]?)?\d{3,4}[\s.\-]\d{3,4}[\s.\-]?\d{0,4}"), WARNING),
    ("long_digit_run", re.compile(r"\b\d{13,19}\b"), WARNING),
)

# Campos cuyo valor es un UUID legítimo y por tanto exento de la regla "uuid".
UUID_EXEMPT_FIELDS = frozenset({"capsule_id", "contributor_id", "idempotency_key"})

# Campos numéricos/estructurales exentos del patrón "phone" y "long_digit_run":
# son conteos y versiones, no datos personales.
NUMERIC_EXEMPT_FIELDS = frozenset({
    "event_count", "schema_version", "client_version", "policy_version",
    "generated_period", "generated_at", "minimum_cohort",
})

MIN_ENTROPY_LEN = 32
MIN_ENTROPY_BITS = 4.0


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts: dict[str, int] = {}
    for ch in value:
        counts[ch] = counts.get(ch, 0) + 1
    total = len(value)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def _luhn_ok(digits: str) -> bool:
    total = 0
    for index, ch in enumerate(reversed(digits)):
        digit = ord(ch) - 48
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def scan_text(text: str, field: str = "<text>") -> list[Finding]:
    """Inspecciona una cadena. Devuelve hallazgos sin exponer el valor."""
    findings: list[Finding] = []
    for kind, pattern, level in PATTERNS:
        if kind == "uuid" and field in UUID_EXEMPT_FIELDS:
            continue
        if kind in ("phone", "long_digit_run") and field in NUMERIC_EXEMPT_FIELDS:
            continue
        for match in pattern.finditer(text):
            value = match.group(0)
            if kind == "long_digit_run":
                # Sólo alarma si además pasa Luhn: candidato real a tarjeta.
                digits = re.sub(r"\D", "", value)
                level_here = BLOCK if _luhn_ok(digits) else WARNING
                findings.append(Finding("possible_card_number" if level_here == BLOCK else kind,
                                        level_here, field, match.start(), len(value)))
                continue
            findings.append(Finding(kind, level, field, match.start(), len(value)))

    # Cadenas largas de alta entropía: candidato genérico a credencial.
    for token in re.findall(r"[A-Za-z0-9+/=_\-]{%d,}" % MIN_ENTROPY_LEN, text):
        if shannon_entropy(token) >= MIN_ENTROPY_BITS:
            already = any(f.field == field and f.position <= text.find(token) < f.position + f.length
                          for f in findings)
            if not already:
                findings.append(Finding("high_entropy_string", BLOCK, field, text.find(token), len(token)))
    return findings


def scan_object(obj: Any, prefix: str = "") -> list[Finding]:
    """Recorre una estructura JSON y escanea claves y valores de texto."""
    findings: list[Finding] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            findings.extend(scan_text(str(key), field=f"{path} (clave)"))
            findings.extend(scan_object(value, path))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            findings.extend(scan_object(value, f"{prefix}[{index}]"))
    elif isinstance(obj, str):
        findings.extend(scan_text(obj, field=prefix or "<root>"))
    return findings


def blocking(findings: Iterable[Finding]) -> list[Finding]:
    return [f for f in findings if f.level == BLOCK]


class PrivacyViolation(Exception):
    """Se lanza cuando una cápsula no puede salir del equipo."""

    def __init__(self, findings: list[Finding]):
        self.findings = findings
        detail = "; ".join(f.describe() for f in findings[:5])
        extra = "" if len(findings) <= 5 else f" (+{len(findings) - 5} más)"
        super().__init__(f"escaneo de privacidad bloqueó el envío: {detail}{extra}")


# ─────────────────────────────────────────────────────────────────────────────
# Allowlist estricta de la cápsula
# ─────────────────────────────────────────────────────────────────────────────
EVENT_FIELDS: dict[str, frozenset[str] | None] = {
    "task_type": frozenset({
        "routine", "content", "implementation", "debugging", "planning",
        "deep_analysis", "architecture", "critical", "research", "unknown",
    }),
    "predicted_gear": frozenset({"G0", "G1", "G2", "G3", "G3.5", "G4", "G5"}),
    "model_family": frozenset({"haiku", "sonnet", "opus", "opusplan", "fable", "other"}),
    "effort": frozenset({"low", "medium", "high", "xhigh", "unknown"}),
    "risk_band": frozenset({"low", "medium", "high"}),
    "complexity_band": frozenset({"low", "medium", "high"}),
    "ambiguity_band": frozenset({"low", "medium", "high"}),
    "routing_confidence_band": None,      # validado por formato de banda
    "predicted_success_band": None,
    "outcome": frozenset({"accepted", "rejected", "rework", "unknown"}),
    "rework": None,                        # bool
    "cost_band": None,
    "latency_band": None,
    "human_override": None,                # bool
    "feedback_reason": frozenset({
        "wrong_gear", "wrong_model", "insufficient_depth", "excessive_cost",
        "incorrect_result", "missing_source", "unnecessary_escalation",
        "needed_human_review", "none",
    }),
    "rating_band": None,
}

CAPSULE_FIELDS = frozenset({
    "schema_version", "client_version", "capsule_id", "generated_period",
    "contribution_mode", "events", "aggregate",
})

AGGREGATE_FIELDS = frozenset({"event_count"})

MAX_EVENTS = 1000
BAND_RE = re.compile(r"^(?:unknown|\d+(?:\.\d+)?-\d+(?:\.\d+)?|\d+\+)$")
PERIOD_RE = re.compile(r"^\d{4}-W\d{2}$|^\d{4}-\d{2}-\d{2}$")

# Nunca, bajo ninguna circunstancia, dentro de una cápsula (§3).
FORBIDDEN_KEYS = frozenset({
    "prompt", "prompt_hash", "prompt_text", "response", "completion", "task_id",
    "session_id", "session_ref", "project_id", "project_ref", "cwd", "repo",
    "branch", "commit", "filename", "file", "path", "url", "ip", "email",
    "phone", "hostname", "username", "user", "token", "secret", "api_key",
    "apikey", "document", "content", "reason", "feedback", "comment", "note",
    "stack_trace", "traceback", "matched_signals", "signals", "created_at",
    "updated_at", "timestamp", "ts", "geo", "country", "region", "locale",
})


def validate_capsule(capsule: Any) -> list[str]:
    """Valida contra la allowlist. Devuelve lista de errores (vacía = válida)."""
    errors: list[str] = []
    if not isinstance(capsule, dict):
        return ["la cápsula debe ser un objeto JSON"]

    unknown = set(capsule) - CAPSULE_FIELDS
    if unknown:
        errors.append(f"campos no permitidos en la cápsula: {sorted(unknown)}")
    for required in ("schema_version", "client_version", "capsule_id",
                     "generated_period", "contribution_mode", "events", "aggregate"):
        if required not in capsule:
            errors.append(f"falta el campo obligatorio: {required}")

    forbidden = FORBIDDEN_KEYS & set(capsule)
    if forbidden:
        errors.append(f"campos prohibidos presentes: {sorted(forbidden)}")

    period = capsule.get("generated_period", "")
    if isinstance(period, str) and period and not PERIOD_RE.match(period):
        errors.append("generated_period debe ser AAAA-Www o AAAA-MM-DD (nunca hora exacta)")

    mode = capsule.get("contribution_mode")
    if mode not in ("community", "self-hosted"):
        errors.append("contribution_mode inválido")

    events = capsule.get("events")
    if not isinstance(events, list):
        errors.append("events debe ser una lista")
        return errors
    # Tope por CANTIDAD, no sólo por bytes: eventos repetidos comprimen tanto que
    # una cápsula enorme cabe en pocos KiB y burlaría un límite de tamaño.
    if len(events) > MAX_EVENTS:
        errors.append(f"demasiados eventos ({len(events)} > {MAX_EVENTS})")
        return errors

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"events[{index}] debe ser un objeto")
            continue
        unknown_ev = set(event) - set(EVENT_FIELDS)
        if unknown_ev:
            errors.append(f"events[{index}]: campos no permitidos {sorted(unknown_ev)}")
        forbidden_ev = FORBIDDEN_KEYS & set(event)
        if forbidden_ev:
            errors.append(f"events[{index}]: campos prohibidos {sorted(forbidden_ev)}")
        for key, value in event.items():
            allowed = EVENT_FIELDS.get(key)
            if allowed is not None and value not in allowed:
                errors.append(f"events[{index}].{key}: valor fuera del enum permitido")
            if key in ("rework", "human_override") and not isinstance(value, bool):
                errors.append(f"events[{index}].{key} debe ser booleano")
            # Las bandas numéricas se validan por formato; las categóricas
            # (risk/complexity/ambiguity) ya tienen su propio enum arriba.
            if (key.endswith("_band") and allowed is None
                    and isinstance(value, str) and not BAND_RE.match(value)):
                errors.append(f"events[{index}].{key} no tiene formato de banda")
            if isinstance(value, str) and len(value) > 32:
                errors.append(f"events[{index}].{key}: cadena demasiado larga (posible texto libre)")

    aggregate = capsule.get("aggregate")
    if isinstance(aggregate, dict):
        unknown_agg = set(aggregate) - AGGREGATE_FIELDS
        if unknown_agg:
            errors.append(f"aggregate: campos no permitidos {sorted(unknown_agg)}")
        count = aggregate.get("event_count")
        if not isinstance(count, int) or isinstance(count, bool):
            errors.append("aggregate.event_count debe ser entero")
        elif isinstance(events, list) and count != len(events):
            errors.append("aggregate.event_count no coincide con events")
    else:
        errors.append("aggregate debe ser un objeto")
    return errors


def assert_safe(capsule: dict[str, Any]) -> None:
    """Valida allowlist y escanea. Lanza PrivacyViolation o ValueError."""
    errors = validate_capsule(capsule)
    if errors:
        raise ValueError("cápsula inválida: " + "; ".join(errors))
    findings = blocking(scan_object(capsule))
    if findings:
        raise PrivacyViolation(findings)


# ─────────────────────────────────────────────────────────────────────────────
# Generalización a bandas
# ─────────────────────────────────────────────────────────────────────────────
def probability_band(value: Any, width: float = 0.1) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unknown"
    number = max(0.0, min(1.0, number))
    low = math.floor(number / width) * width
    if low >= 1.0:
        low = 1.0 - width
    return f"{low:.1f}-{low + width:.1f}"


def level_band(value: Any, low: float = 0.34, high: float = 0.67) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if number < low:
        return "low"
    if number < high:
        return "medium"
    return "high"


SAMPLE_BANDS = ((0, 9), (10, 24), (25, 49), (50, 99), (100, 249), (250, 499), (500, 999))


def sample_band(count: int) -> str:
    for low, high in SAMPLE_BANDS:
        if low <= count <= high:
            return f"{low}-{high}"
    return "1000+"


def rating_band(value: Any) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return "unknown"
    if number <= 2:
        return "1-2"
    if number == 3:
        return "3-3"
    return "4-5"


def model_family(model: str) -> str:
    lowered = (model or "").lower()
    for family in ("haiku", "opusplan", "opus", "sonnet", "fable"):
        if family in lowered:
            return family
    return "other"


def iso_week(dt) -> str:
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


# ─────────────────────────────────────────────────────────────────────────────
# Seudónimos locales (nunca se transmiten)
# ─────────────────────────────────────────────────────────────────────────────
def local_ref(salt: bytes, value: str, length: int = 16) -> str:
    """HMAC-SHA256 con sal local. Sustituye rutas/ids crudos en la base local.

    No es reversible sin la sal, y la sal nunca sale del equipo. Dos instalaciones
    distintas producen refs distintos para la misma ruta: no son correlacionables.
    """
    if not value:
        return ""
    return hmac.new(salt, value.encode("utf-8", errors="replace"), sha256).hexdigest()[:length]


def canonical_json(value: Any) -> bytes:
    """JSON canónico y determinista para hashing/firma."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return sha256(data).hexdigest()
