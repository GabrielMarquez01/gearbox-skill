"""Controles de seguridad del colector de referencia.

Todo lo que se aplica ANTES de mirar el contenido: tamaño, descompresión
acotada, autenticación, límite de tasa, anti-replay y frescura. Ninguno de estos
controles registra el payload ni el token.
"""
from __future__ import annotations

import hmac
import os
import re
import time
import zlib
from dataclasses import dataclass, field
from typing import Any

MAX_BODY_BYTES = 512 * 1024              # comprimido
MAX_DECOMPRESSED_BYTES = 4 * 1024 * 1024  # tope duro anti zip-bomb
MAX_COMPRESSION_RATIO = 200               # 4 MiB / 20 KiB ≈ 200
RATE_LIMIT_PER_HOUR = 12
REPLAY_WINDOW_SECONDS = 24 * 3600
MAX_PERIOD_AGE_WEEKS = 8

PERIOD_RE = re.compile(r"^(\d{4})-W(\d{2})$|^(\d{4})-(\d{2})-(\d{2})$")


class RejectedRequest(Exception):
    """Rechazo estructurado: código estable + status HTTP."""

    def __init__(self, code: str, status: int = 400, detail: str = ""):
        self.code = code
        self.status = status
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def safe_gunzip(data: bytes) -> bytes:
    """Descomprime gzip con tope duro. Una bomba se corta, no revienta memoria."""
    if len(data) > MAX_BODY_BYTES:
        raise RejectedRequest("payload_too_large", 413, f"{len(data)} bytes comprimidos")
    decompressor = zlib.decompressobj(wbits=31)  # 31 = gzip
    try:
        out = decompressor.decompress(data, MAX_DECOMPRESSED_BYTES + 1)
    except zlib.error as exc:
        raise RejectedRequest("invalid_gzip", 400, type(exc).__name__) from exc
    if len(out) > MAX_DECOMPRESSED_BYTES or not decompressor.eof:
        raise RejectedRequest("decompression_bomb", 413,
                              f"supera {MAX_DECOMPRESSED_BYTES} bytes descomprimidos")
    if data and len(out) / max(1, len(data)) > MAX_COMPRESSION_RATIO:
        raise RejectedRequest("decompression_bomb", 413, "ratio de compresión sospechoso")
    return out


def check_auth(headers: dict[str, str], expected_token: str | None) -> None:
    """Autenticación configurable. Sin token configurado, el colector es abierto
    (sólo apto para desarrollo local: el README lo advierte)."""
    if not expected_token:
        return
    raw = headers.get("authorization", "")
    if not raw.lower().startswith("bearer "):
        raise RejectedRequest("unauthorized", 401)
    presented = raw.split(None, 1)[1].strip()
    if not hmac.compare_digest(presented, expected_token):
        raise RejectedRequest("unauthorized", 401)


@dataclass
class RateLimiter:
    """Ventana deslizante por contribuyente. En memoria, suficiente para la
    referencia; en producción debe vivir en el borde o en un almacén compartido."""

    limit: int = RATE_LIMIT_PER_HOUR
    window: int = 3600
    _hits: dict[str, list[float]] = field(default_factory=dict)

    def check(self, key: str, now: float | None = None) -> None:
        now = time.time() if now is None else now
        bucket = [t for t in self._hits.get(key, []) if now - t < self.window]
        if len(bucket) >= self.limit:
            bucket_reset = int(self.window - (now - bucket[0]))
            self._hits[key] = bucket
            raise RejectedRequest("rate_limited", 429, f"reintenta en {bucket_reset}s")
        bucket.append(now)
        self._hits[key] = bucket


def content_hash_ok(declared: str | None, computed: str) -> None:
    if declared and not hmac.compare_digest(declared.lower(), computed.lower()):
        raise RejectedRequest("content_hash_mismatch", 400)


def check_period_freshness(period: str, now: float | None = None) -> None:
    """Anti-replay temporal: una cápsula de hace meses no se acepta."""
    match = PERIOD_RE.match(period or "")
    if not match:
        raise RejectedRequest("invalid_period", 422)
    now = time.time() if now is None else now
    if match.group(1):
        year, week = int(match.group(1)), int(match.group(2))
        if not 1 <= week <= 53:
            raise RejectedRequest("invalid_period", 422)
        current = time.gmtime(now)
        current_year = current.tm_year
        current_week = int(time.strftime("%V", current))
        age_weeks = (current_year - year) * 52 + (current_week - week)
    else:
        year, month, day = int(match.group(3)), int(match.group(4)), int(match.group(5))
        try:
            stamp = time.mktime((year, month, day, 0, 0, 0, 0, 0, 0))
        except (ValueError, OverflowError) as exc:
            raise RejectedRequest("invalid_period", 422) from exc
        age_weeks = (now - stamp) / (7 * 86400)
    if age_weeks > MAX_PERIOD_AGE_WEEKS:
        raise RejectedRequest("period_too_old", 422, f"{int(age_weeks)} semanas")
    if age_weeks < -1:
        raise RejectedRequest("period_in_future", 422)


def redact_for_log(value: Any) -> str:
    """Los logs del colector NUNCA llevan payload. Sólo metadatos acotados."""
    text = str(value)
    text = re.sub(r"(?i)bearer\s+\S+", "bearer «redactado»", text)
    return text[:200]


def expected_token() -> str | None:
    return (os.environ.get("GEARBOX_COLLECTOR_TOKEN") or "").strip() or None
