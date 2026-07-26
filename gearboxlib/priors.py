"""Cliente de priors comunitarios agregados.

Qué recibe el cliente: **sólo agregados con bandas**, nunca cápsulas ni filas
individuales. Qué hace con ellos: usarlos como *prior inicial* cuando aún no hay
evidencia local. Qué NO hace nunca: relajar un gate humano ni sobreescribir la
política local (§8 de la misión).

Verificación: schema estricto + SHA-256 del contenido canónico. La firma
criptográfica se soporta como HMAC-SHA256 con clave compartida
(``GEARBOX_PRIORS_HMAC_KEY``); la firma asimétrica de producción queda declarada
como **pendiente de infraestructura** y no se simula.
"""
from __future__ import annotations

import hmac
import re
from hashlib import sha256
from pathlib import Path
from typing import Any

from .paths import atomic_write_json, gb_dir, read_json
from . import privacy

MINIMUM_COHORT = 20
BAND_RE = re.compile(r"^\d+(?:\.\d+)?-\d+(?:\.\d+)?$|^\d+\+$")
SUPPORTED_SCHEMA = "1.0"


def priors_path() -> Path:
    return gb_dir() / "community-priors.json"


class PriorsRejected(Exception):
    pass


def content_digest(document: dict[str, Any]) -> str:
    """SHA-256 del documento sin su bloque de integridad."""
    payload = {k: v for k, v in document.items() if k not in ("content_sha256", "signature")}
    return privacy.sha256_hex(privacy.canonical_json(payload))


def validate(document: Any, *, hmac_key: bytes | None = None) -> list[str]:
    """Valida estructura, umbral de cohorte, hash y (si aplica) firma."""
    errors: list[str] = []
    if not isinstance(document, dict):
        return ["el documento de priors debe ser un objeto JSON"]

    schema = str(document.get("schema_version", ""))
    if schema != SUPPORTED_SCHEMA:
        errors.append(f"schema_version incompatible: {schema or '(ausente)'}")

    minimum = document.get("minimum_cohort")
    if not isinstance(minimum, int) or minimum < MINIMUM_COHORT:
        errors.append(f"minimum_cohort debe ser un entero ≥ {MINIMUM_COHORT}")

    routes = document.get("routes")
    if not isinstance(routes, list):
        errors.append("routes debe ser una lista")
        routes = []

    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            errors.append(f"routes[{index}] debe ser un objeto")
            continue
        allowed = {"task_type", "gear", "model_family", "effort", "sample_band",
                   "accepted_rate_band", "rework_rate_band"}
        unknown = set(route) - allowed
        if unknown:
            errors.append(f"routes[{index}]: campos no permitidos {sorted(unknown)}")
        for key in ("sample_band", "accepted_rate_band", "rework_rate_band"):
            value = route.get(key)
            if not isinstance(value, str) or not BAND_RE.match(value):
                errors.append(f"routes[{index}].{key} debe ser una banda, no una cifra exacta")
        if route.get("gear") not in privacy.EVENT_FIELDS["predicted_gear"]:
            errors.append(f"routes[{index}].gear fuera del enum")
        if route.get("task_type") not in privacy.EVENT_FIELDS["task_type"]:
            errors.append(f"routes[{index}].task_type fuera del enum")
        # Cohorte insuficiente: no debió publicarse. Se rechaza el documento.
        band = route.get("sample_band")
        if isinstance(band, str) and BAND_RE.match(band):
            low = float(band.split("-")[0].rstrip("+"))
            if low < MINIMUM_COHORT:
                errors.append(
                    f"routes[{index}]: sample_band {band} viola el mínimo de cohorte "
                    f"({MINIMUM_COHORT})"
                )

    declared = document.get("content_sha256")
    if declared:
        if declared != content_digest(document):
            errors.append("content_sha256 no coincide: documento alterado o corrupto")
    else:
        errors.append("falta content_sha256")

    signature = document.get("signature")
    if hmac_key:
        if not isinstance(signature, dict) or signature.get("alg") != "HMAC-SHA256":
            errors.append("falta firma HMAC-SHA256 y hay clave configurada")
        else:
            expected = hmac.new(hmac_key, content_digest(document).encode(), sha256).hexdigest()
            if not hmac.compare_digest(expected, str(signature.get("value", ""))):
                errors.append("firma inválida")
    return errors


def store(document: dict[str, Any], *, hmac_key: bytes | None = None) -> dict[str, Any]:
    """Guarda el documento sólo si es válido. Si no, conserva el último válido."""
    errors = validate(document, hmac_key=hmac_key)
    if errors:
        raise PriorsRejected("; ".join(errors))
    atomic_write_json(priors_path(), document, private=False, indent=2)
    return document


def load() -> dict[str, Any] | None:
    document = read_json(priors_path(), None)
    if not isinstance(document, dict):
        return None
    if validate(document):     # se revalida al leer: un archivo tocado en disco no pasa
        return None
    return document


def _band_center(band: str) -> float:
    if band.endswith("+"):
        return float(band[:-1])
    low, _, high = band.partition("-")
    try:
        return (float(low) + float(high)) / 2.0
    except ValueError:
        return 0.0


def lookup(task_type: str, gear: str, model_family: str, effort: str) -> float | None:
    """Tasa de aceptación comunitaria (centro de banda) para una ruta, si existe."""
    document = load()
    if not document:
        return None
    for route in document.get("routes", []):
        if (route.get("task_type") == task_type and route.get("gear") == gear
                and route.get("model_family") == model_family and route.get("effort") == effort):
            return _band_center(str(route.get("accepted_rate_band", "")))
    return None


def blended_prior(local_prior: float, community_rate: float | None, local_samples: int,
                  *, community_weight: float = 4.0) -> float:
    """Combina prior local y comunitario dando peso decreciente a la comunidad.

    Con 0 muestras locales el prior comunitario domina; conforme el usuario
    acumula evidencia propia, su historia manda. Nunca sustituye al gate humano:
    esto sólo afecta a ``predicted_success``, no a ``human_gate``.
    """
    if community_rate is None:
        return local_prior
    weight = community_weight / (community_weight + max(0, local_samples))
    return (weight * community_rate) + ((1.0 - weight) * local_prior)


def summary() -> dict[str, Any]:
    document = load()
    if not document:
        return {"available": False, "routes": 0}
    return {
        "available": True,
        "schema_version": document.get("schema_version"),
        "generated_at": document.get("generated_at"),
        "minimum_cohort": document.get("minimum_cohort"),
        "routes": len(document.get("routes", [])),
        "content_sha256": document.get("content_sha256"),
        "signed": bool(document.get("signature")),
    }
