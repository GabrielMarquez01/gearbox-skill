"""Cola de salida transaccional. Nada se pierde en silencio; nada se duplica.

Garantías (§5 de la misión):

* transacciones SQLite e idempotencia por ``capsule_id`` (PRIMARY KEY);
* reintentos con backoff exponencial + jitter determinista por cápsula;
* límite de tamaño e intentos configurable;
* retención máxima y purga de expirados;
* el hook ``UserPromptSubmit`` NUNCA toca esta cola ni la red.
"""
from __future__ import annotations

import gzip
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .paths import ensure_private_dir, gb_dir, harden
from . import privacy

STATUS_PENDING = "pending"
STATUS_SENT = "sent"
STATUS_FAILED = "failed"
STATUS_EXPIRED = "expired"

MAX_ATTEMPTS = 6
BASE_BACKOFF_SECONDS = 60
MAX_BACKOFF_SECONDS = 6 * 3600
RETENTION_DAYS = 14
MAX_PAYLOAD_BYTES = 512 * 1024          # 512 KiB comprimidos
MAX_QUEUE_ITEMS = 200


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def outbox_dir() -> Path:
    return ensure_private_dir(gb_dir() / "outbox")


def db_path() -> Path:
    return gb_dir() / "telemetry.db"


def connect() -> sqlite3.Connection:
    ensure_private_dir(gb_dir())
    conn = sqlite3.connect(db_path(), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_outbox (
            capsule_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            compressed_path TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            next_attempt_at TEXT,
            last_error_code TEXT,
            consent_version TEXT NOT NULL,
            byte_size INTEGER NOT NULL DEFAULT 0,
            sent_at TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status ON telemetry_outbox(status, next_attempt_at)")
    harden(db_path())
    return conn


class OutboxFull(Exception):
    pass


class PayloadTooLarge(Exception):
    pass


def enqueue(capsule: dict[str, Any], consent_version: str) -> dict[str, Any]:
    """Valida, comprime y encola. Idempotente por capsule_id.

    Lanza ``PrivacyViolation`` (escáner) o ``ValueError`` (allowlist) antes de
    escribir un solo byte: una cápsula inválida nunca llega a la cola.
    """
    privacy.assert_safe(capsule)

    capsule_id = str(capsule["capsule_id"])
    body = privacy.canonical_json(capsule)
    digest = privacy.sha256_hex(body)
    compressed = gzip.compress(body, compresslevel=9, mtime=0)
    if len(compressed) > MAX_PAYLOAD_BYTES:
        raise PayloadTooLarge(
            f"cápsula de {len(compressed)} bytes supera el límite de {MAX_PAYLOAD_BYTES}"
        )

    with connect() as conn:
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM telemetry_outbox WHERE status=?", (STATUS_PENDING,)
        ).fetchone()["n"]
        if pending >= MAX_QUEUE_ITEMS:
            raise OutboxFull(f"la cola ya tiene {pending} paquetes pendientes")

        existing = conn.execute(
            "SELECT capsule_id FROM telemetry_outbox WHERE capsule_id=?", (capsule_id,)
        ).fetchone()
        if existing:
            return dict(conn.execute(
                "SELECT * FROM telemetry_outbox WHERE capsule_id=?", (capsule_id,)
            ).fetchone())

        path = outbox_dir() / f"{capsule_id}.json.gz"
        tmp = path.with_suffix(".gz.tmp")
        tmp.write_bytes(compressed)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)

        now = _now()
        conn.execute(
            """
            INSERT INTO telemetry_outbox (
                capsule_id, created_at, schema_version, payload_sha256,
                compressed_path, status, attempts, next_attempt_at,
                consent_version, byte_size
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                capsule_id, _iso(now), str(capsule.get("schema_version", "1.0")), digest,
                str(path), STATUS_PENDING, 0, _iso(now), consent_version, len(compressed),
            ),
        )
        return dict(conn.execute(
            "SELECT * FROM telemetry_outbox WHERE capsule_id=?", (capsule_id,)
        ).fetchone())


def backoff_seconds(attempts: int, capsule_id: str) -> int:
    """Backoff exponencial con jitter determinista (derivado del capsule_id).

    Determinista para que sea reproducible en pruebas, y distinto entre clientes
    para no sincronizar reintentos contra el colector.
    """
    base = min(BASE_BACKOFF_SECONDS * (2 ** max(0, attempts - 1)), MAX_BACKOFF_SECONDS)
    jitter_ratio = int(privacy.sha256_hex(capsule_id.encode())[:4], 16) / 0xFFFF  # 0..1
    jitter = int(base * 0.3 * jitter_ratio)
    return base + jitter


def due(now: datetime | None = None, limit: int = 10) -> list[dict[str, Any]]:
    now = now or _now()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM telemetry_outbox
            WHERE status=? AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
            ORDER BY created_at ASC LIMIT ?
            """,
            (STATUS_PENDING, _iso(now), limit),
        ).fetchall()
    return [dict(row) for row in rows]


def payload(entry: dict[str, Any]) -> bytes:
    return Path(entry["compressed_path"]).read_bytes()


def mark_sent(capsule_id: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE telemetry_outbox SET status=?, sent_at=?, last_error_code=NULL WHERE capsule_id=?",
            (STATUS_SENT, _iso(_now()), capsule_id),
        )
    _drop_file(capsule_id)


def mark_failed(capsule_id: str, error_code: str, *, now: datetime | None = None) -> str:
    """Registra el fallo y programa el siguiente intento. Devuelve el estado."""
    now = now or _now()
    with connect() as conn:
        row = conn.execute(
            "SELECT attempts FROM telemetry_outbox WHERE capsule_id=?", (capsule_id,)
        ).fetchone()
        if row is None:
            return "unknown"
        attempts = int(row["attempts"]) + 1
        if attempts >= MAX_ATTEMPTS:
            conn.execute(
                "UPDATE telemetry_outbox SET status=?, attempts=?, last_error_code=? WHERE capsule_id=?",
                (STATUS_FAILED, attempts, error_code, capsule_id),
            )
            return STATUS_FAILED
        nxt = now + timedelta(seconds=backoff_seconds(attempts, capsule_id))
        conn.execute(
            """
            UPDATE telemetry_outbox
            SET attempts=?, next_attempt_at=?, last_error_code=?, status=?
            WHERE capsule_id=?
            """,
            (attempts, _iso(nxt), error_code, STATUS_PENDING, capsule_id),
        )
        return STATUS_PENDING


def _drop_file(capsule_id: str) -> None:
    try:
        (outbox_dir() / f"{capsule_id}.json.gz").unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def purge_expired(retention_days: int = RETENTION_DAYS, now: datetime | None = None) -> int:
    """Elimina paquetes más viejos que la retención. Deja rastro del conteo."""
    now = now or _now()
    cutoff = now - timedelta(days=retention_days)
    removed = 0
    with connect() as conn:
        rows = conn.execute(
            "SELECT capsule_id, created_at, status FROM telemetry_outbox"
        ).fetchall()
        for row in rows:
            created = _parse(row["created_at"])
            if created is None or created > cutoff:
                continue
            if row["status"] == STATUS_SENT:
                conn.execute("DELETE FROM telemetry_outbox WHERE capsule_id=?", (row["capsule_id"],))
            else:
                conn.execute(
                    "UPDATE telemetry_outbox SET status=? WHERE capsule_id=?",
                    (STATUS_EXPIRED, row["capsule_id"]),
                )
            _drop_file(str(row["capsule_id"]))
            removed += 1
    return removed


def purge_all() -> int:
    """Vacía la cola por completo (revocación o `telemetry purge`)."""
    with connect() as conn:
        rows = conn.execute("SELECT capsule_id FROM telemetry_outbox").fetchall()
        for row in rows:
            _drop_file(str(row["capsule_id"]))
        conn.execute("DELETE FROM telemetry_outbox")
        count = len(rows)
    for leftover in outbox_dir().glob("*.gz"):
        try:
            leftover.unlink()
        except OSError:
            pass
    return count


def stats() -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n, COALESCE(SUM(byte_size),0) AS bytes "
            "FROM telemetry_outbox GROUP BY status"
        ).fetchall()
    result: dict[str, Any] = {"pending": 0, "sent": 0, "failed": 0, "expired": 0, "bytes": 0}
    for row in rows:
        result[str(row["status"])] = int(row["n"])
        result["bytes"] += int(row["bytes"])
    return result


def entries(limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT capsule_id, created_at, status, attempts, next_attempt_at, "
            "last_error_code, byte_size FROM telemetry_outbox "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
