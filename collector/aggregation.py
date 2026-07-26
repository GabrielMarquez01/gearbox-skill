"""Agregación con umbral de cohorte y publicación de priors comunitarios.

Reglas de protección estadística (§8):

* nunca se publica una combinación con ``n < MINIMUM_COHORT`` (20);
* además se exige un mínimo de **contribuyentes distintos** (5): 20 eventos de
  una sola persona no son una cohorte, son un diario;
* sólo se publican **bandas**, jamás cifras exactas;
* no hay dimensión geográfica, temporal fina ni identificadores.

La privacidad diferencial NO está implementada. Se documenta como trabajo futuro
en COMMUNITY-LEARNING.md; aquí no se simula.
"""
from __future__ import annotations

import hmac
import json
import os
import time
from hashlib import sha256
from typing import Any

MINIMUM_COHORT = 20
MINIMUM_CONTRIBUTORS = 5
SCHEMA_VERSION = "1.0"

SAMPLE_BANDS = ((0, 9), (10, 24), (25, 49), (50, 99), (100, 249), (250, 499), (500, 999))


def sample_band(count: int) -> str:
    for low, high in SAMPLE_BANDS:
        if low <= count <= high:
            return f"{low}-{high}"
    return "1000+"


def rate_band(numerator: int, denominator: int, width: float = 0.1) -> str:
    if denominator <= 0:
        return "0.0-0.1"
    rate = max(0.0, min(1.0, numerator / denominator))
    low = int(rate / width) * width
    if low >= 1.0:
        low = 1.0 - width
    return f"{low:.1f}-{low + width:.1f}"


def aggregate_pending(storage) -> dict[str, int]:
    """Procesa cápsulas crudas → agregados y BORRA la cruda. Idempotente."""
    processed = events = 0
    for row in storage.pending_raw():
        try:
            capsule = json.loads(row["body"])
        except json.JSONDecodeError:
            storage.drop_raw(str(row["capsule_id"]))
            continue
        contributor = row["contributor_id"]
        buckets: dict[tuple[str, str, str, str], dict[str, int]] = {}
        for event in capsule.get("events", []):
            key = (
                str(event.get("task_type", "unknown")),
                str(event.get("predicted_gear", "G2")),
                str(event.get("model_family", "other")),
                str(event.get("effort", "unknown")),
            )
            bucket = buckets.setdefault(key, {"samples": 0, "accepted": 0, "rework": 0})
            bucket["samples"] += 1
            if event.get("outcome") == "accepted":
                bucket["accepted"] += 1
            if event.get("rework") is True:
                bucket["rework"] += 1
            events += 1
        for key, bucket in buckets.items():
            storage.upsert_aggregate(
                key, accepted=bucket["accepted"], rework=bucket["rework"],
                samples=bucket["samples"], contributor_id=contributor,
            )
        storage.drop_raw(str(row["capsule_id"]))
        processed += 1
    return {"capsules_aggregated": processed, "events_aggregated": events}


def suppressed_reason(samples: int, contributors: int) -> str | None:
    if samples < MINIMUM_COHORT:
        return "cohorte insuficiente"
    if contributors < MINIMUM_CONTRIBUTORS:
        return "pocos contribuyentes distintos"
    return None


def build_priors(storage, *, hmac_key: bytes | None = None) -> dict[str, Any]:
    """Genera community-priors.json. Sólo entran celdas que superan el umbral."""
    routes: list[dict[str, Any]] = []
    suppressed = 0
    for row in storage.aggregates():
        contributors = len(json.loads(row["contributors"]))
        samples = int(row["samples"])
        if suppressed_reason(samples, contributors):
            suppressed += 1
            continue
        routes.append({
            "task_type": row["task_type"],
            "gear": row["gear"],
            "model_family": row["model_family"],
            "effort": row["effort"],
            "sample_band": sample_band(samples),
            "accepted_rate_band": rate_band(int(row["accepted"]), samples),
            "rework_rate_band": rate_band(int(row["rework"]), samples),
        })

    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": time.strftime("%Y-%m-%d", time.gmtime()),
        "minimum_cohort": MINIMUM_COHORT,
        "routes": sorted(routes, key=lambda r: (r["task_type"], r["gear"], r["model_family"])),
    }
    document["content_sha256"] = _digest(document)
    if hmac_key:
        document["signature"] = {
            "alg": "HMAC-SHA256",
            "value": hmac.new(hmac_key, document["content_sha256"].encode(), sha256).hexdigest(),
        }
    document["_suppressed_cells"] = suppressed
    # El conteo de celdas suprimidas es metadato operativo: se reporta en /health,
    # no dentro del documento firmado.
    document.pop("_suppressed_cells")
    return document


def _digest(document: dict[str, Any]) -> str:
    payload = {k: v for k, v in document.items() if k not in ("content_sha256", "signature")}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def hmac_key_from_env() -> bytes | None:
    value = (os.environ.get("GEARBOX_PRIORS_HMAC_KEY") or "").strip()
    return value.encode("utf-8") if value else None
