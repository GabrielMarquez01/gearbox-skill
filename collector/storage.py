"""Almacenamiento del colector: ingestión cruda efímera + agregados persistentes.

Separación deliberada (§7): la ingestión escribe en ``raw_capsules``, la
agregación lee de ahí, escribe en ``aggregates`` y **borra la cruda**. Los
agregados no permiten reconstruir una cápsula individual.

Retención por defecto: 7 días, con tope duro de 30. Una configuración más corta
siempre se acepta; una más larga se recorta a 30 y se anota.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

DEFAULT_RETENTION_DAYS = 7
MAX_RETENTION_DAYS = 30


def retention_days() -> int:
    try:
        value = int(os.environ.get("GEARBOX_COLLECTOR_RETENTION_DAYS", DEFAULT_RETENTION_DAYS))
    except ValueError:
        return DEFAULT_RETENTION_DAYS
    return max(1, min(value, MAX_RETENTION_DAYS))


class Storage:
    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS raw_capsules (
                capsule_id TEXT PRIMARY KEY,
                received_at REAL NOT NULL,
                contributor_id TEXT,
                schema_version TEXT NOT NULL,
                generated_period TEXT NOT NULL,
                event_count INTEGER NOT NULL,
                body TEXT NOT NULL,
                aggregated INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS aggregates (
                task_type TEXT NOT NULL,
                gear TEXT NOT NULL,
                model_family TEXT NOT NULL,
                effort TEXT NOT NULL,
                samples INTEGER NOT NULL DEFAULT 0,
                accepted INTEGER NOT NULL DEFAULT 0,
                rework INTEGER NOT NULL DEFAULT 0,
                contributors TEXT NOT NULL DEFAULT '[]',
                updated_at REAL NOT NULL,
                PRIMARY KEY (task_type, gear, model_family, effort)
            );
            CREATE TABLE IF NOT EXISTS deletion_requests (
                request_id TEXT PRIMARY KEY,
                contributor_id TEXT NOT NULL,
                requested_at REAL NOT NULL,
                completed_at REAL,
                raw_deleted INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS metrics (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL DEFAULT 0
            );
            """
        )

    # ── ingestión ────────────────────────────────────────────────────────────
    def seen(self, capsule_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM raw_capsules WHERE capsule_id=?", (capsule_id,)
        ).fetchone()
        if row:
            return True
        # También cuenta como visto si ya se agregó y se borró la cruda.
        row = self.conn.execute(
            "SELECT 1 FROM metrics WHERE key=?", (f"seen:{capsule_id}",)
        ).fetchone()
        return bool(row)

    def store_capsule(self, capsule: dict[str, Any], contributor_id: str | None) -> None:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO raw_capsules
                (capsule_id, received_at, contributor_id, schema_version,
                 generated_period, event_count, body)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                str(capsule["capsule_id"]), time.time(), contributor_id,
                str(capsule["schema_version"]), str(capsule["generated_period"]),
                int(capsule["aggregate"]["event_count"]),
                json.dumps(capsule, ensure_ascii=False, separators=(",", ":")),
            ),
        )
        self.bump("capsules_received")

    def bump(self, key: str, amount: int = 1) -> None:
        self.conn.execute(
            "INSERT INTO metrics(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = value + excluded.value",
            (key, amount),
        )

    def mark_seen(self, capsule_id: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO metrics(key, value) VALUES(?, 1)", (f"seen:{capsule_id}",)
        )

    # ── agregación ───────────────────────────────────────────────────────────
    def pending_raw(self, limit: int = 1000) -> list[sqlite3.Row]:
        return list(self.conn.execute(
            "SELECT * FROM raw_capsules WHERE aggregated=0 ORDER BY received_at LIMIT ?",
            (limit,),
        ))

    def upsert_aggregate(self, key: tuple[str, str, str, str], *, accepted: int,
                         rework: int, samples: int, contributor_id: str | None) -> None:
        row = self.conn.execute(
            "SELECT samples, accepted, rework, contributors FROM aggregates "
            "WHERE task_type=? AND gear=? AND model_family=? AND effort=?",
            key,
        ).fetchone()
        contributors = set(json.loads(row["contributors"])) if row else set()
        if contributor_id:
            contributors.add(contributor_id)
        if row:
            self.conn.execute(
                "UPDATE aggregates SET samples=?, accepted=?, rework=?, contributors=?, "
                "updated_at=? WHERE task_type=? AND gear=? AND model_family=? AND effort=?",
                (row["samples"] + samples, row["accepted"] + accepted, row["rework"] + rework,
                 json.dumps(sorted(contributors)), time.time(), *key),
            )
        else:
            self.conn.execute(
                "INSERT INTO aggregates (task_type, gear, model_family, effort, samples, "
                "accepted, rework, contributors, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (*key, samples, accepted, rework, json.dumps(sorted(contributors)), time.time()),
            )

    def drop_raw(self, capsule_id: str) -> None:
        """Elimina la cápsula cruda tras agregarla. El seudónimo se conserva sólo
        como marca de 'visto' para idempotencia, sin cuerpo ni eventos."""
        self.conn.execute("DELETE FROM raw_capsules WHERE capsule_id=?", (capsule_id,))
        self.mark_seen(capsule_id)
        self.bump("raw_deleted_after_aggregation")

    def purge_expired_raw(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        cutoff = now - retention_days() * 86400
        rows = self.conn.execute(
            "SELECT capsule_id FROM raw_capsules WHERE received_at < ?", (cutoff,)
        ).fetchall()
        for row in rows:
            self.conn.execute("DELETE FROM raw_capsules WHERE capsule_id=?", (row["capsule_id"],))
            self.mark_seen(str(row["capsule_id"]))
        if rows:
            self.bump("raw_expired", len(rows))
        return len(rows)

    def aggregates(self) -> list[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM aggregates ORDER BY samples DESC"))

    # ── derechos del titular ────────────────────────────────────────────────
    def request_deletion(self, request_id: str, contributor_id: str) -> dict[str, Any]:
        """Elimina cápsulas crudas del contribuyente y deja constancia.

        Los agregados YA no son atribuibles a una persona (no guardan el vínculo
        evento→contribuyente), por lo que no se recalculan: el README documenta
        esta decisión y su fundamento.
        """
        rows = self.conn.execute(
            "SELECT capsule_id FROM raw_capsules WHERE contributor_id=?", (contributor_id,)
        ).fetchall()
        for row in rows:
            self.conn.execute("DELETE FROM raw_capsules WHERE capsule_id=?", (row["capsule_id"],))
        self.conn.execute(
            "INSERT OR REPLACE INTO deletion_requests "
            "(request_id, contributor_id, requested_at, completed_at, raw_deleted) "
            "VALUES (?,?,?,?,?)",
            (request_id, contributor_id, time.time(), time.time(), len(rows)),
        )
        self.bump("deletion_requests")
        return {"request_id": request_id, "raw_capsules_deleted": len(rows), "status": "completed"}

    def metrics(self) -> dict[str, int]:
        return {
            str(row["key"]): int(row["value"])
            for row in self.conn.execute("SELECT key, value FROM metrics WHERE key NOT LIKE 'seen:%'")
        }

    def close(self) -> None:
        self.conn.close()
