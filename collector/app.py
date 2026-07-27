"""Colector de referencia. Python estándar, sin dependencias.

NO es un servicio productivo: es la implementación de referencia del contrato,
pensada para leerse, probarse y auto-alojarse. El README enumera lo que falta
antes de exponerlo a internet.

El enrutador (``Collector.handle``) es una función pura sobre
``(método, ruta, cabeceras, cuerpo)`` para poder probarlo sin abrir sockets.
"""
from __future__ import annotations

import json
import sys
import uuid
from hashlib import sha256
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collector import aggregation, schema, security          # noqa: E402
from collector.storage import Storage, retention_days        # noqa: E402

JSON = "application/json"


class Collector:
    def __init__(self, storage: Storage | None = None, *, token: str | None = None,
                 rate_limiter: security.RateLimiter | None = None):
        self.storage = storage or Storage()
        self.token = token
        self.rate_limiter = rate_limiter or security.RateLimiter()

    # ── enrutador ───────────────────────────────────────────────────────────
    def handle(self, method: str, path: str, headers: dict[str, str],
               body: bytes = b"") -> tuple[int, dict[str, str], bytes]:
        headers = {k.lower(): v for k, v in headers.items()}
        try:
            if method == "GET" and path == "/health":
                return self._ok(self.health())
            if method == "GET" and path == "/v1/schema":
                return self._ok(schema.published_schema())
            if method == "GET" and path == "/v1/community-priors/latest":
                return self._ok(self.priors())
            if method == "POST" and path == "/v1/capsules":
                return self.ingest(headers, body)
            if method == "POST" and path == "/v1/deletion-requests":
                return self.deletion(headers, body)
            return self._err(404, "not_found")
        except security.RejectedRequest as exc:
            self.storage.bump(f"rejected:{exc.code}")
            return self._err(exc.status, exc.code, exc.detail)
        except schema.SchemaError as exc:
            self.storage.bump("rejected:schema_invalid")
            return self._err(422, "schema_invalid", "; ".join(exc.errors[:6]))
        except Exception as exc:                     # noqa: BLE001
            # Nunca se filtra el cuerpo ni el detalle interno al cliente.
            self.storage.bump("errors:internal")
            return self._err(500, "internal_error", type(exc).__name__)

    # ── endpoints ───────────────────────────────────────────────────────────
    def ingest(self, headers: dict[str, str], body: bytes) -> tuple[int, dict[str, str], bytes]:
        security.check_auth(headers, self.token)
        contributor = (headers.get("x-gearbox-contributor") or "").strip() or None
        self.rate_limiter.check(contributor or "anonymous")

        if headers.get("content-encoding", "").lower() != "gzip":
            raise security.RejectedRequest("gzip_required", 415)
        raw = security.safe_gunzip(body)
        computed = sha256(raw).hexdigest()
        security.content_hash_ok(headers.get("x-gearbox-content-sha256"), computed)

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise security.RejectedRequest("invalid_json", 400, type(exc).__name__) from exc

        capsule = schema.validate(payload)
        security.check_period_freshness(str(capsule["generated_period"]))

        idempotency = (headers.get("idempotency-key") or "").strip()
        if idempotency and idempotency != str(capsule["capsule_id"]):
            raise security.RejectedRequest("idempotency_mismatch", 400)

        if self.storage.seen(str(capsule["capsule_id"])):
            self.storage.bump("duplicates_ignored")
            return self._ok({"status": "duplicate", "capsule_id": capsule["capsule_id"]})

        self.storage.store_capsule(capsule, contributor)
        return self._ok({
            "status": "accepted",
            "capsule_id": capsule["capsule_id"],
            "events": capsule["aggregate"]["event_count"],
            "retention_days": retention_days(),
        }, status=202)

    def deletion(self, headers: dict[str, str], body: bytes) -> tuple[int, dict[str, str], bytes]:
        security.check_auth(headers, self.token)
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise security.RejectedRequest("invalid_json", 400) from exc
        contributor = str(payload.get("contributor_id", "")).strip()
        if not contributor or len(contributor) > 64:
            raise security.RejectedRequest("contributor_id_required", 400)
        result = self.storage.request_deletion(str(uuid.uuid4()), contributor)
        result["note"] = ("Los agregados no conservan el vínculo evento→contribuyente "
                          "y por tanto ya no son datos personales atribuibles.")
        return self._ok(result, status=202)

    def priors(self) -> dict[str, Any]:
        aggregation.aggregate_pending(self.storage)
        return aggregation.build_priors(self.storage, hmac_key=aggregation.hmac_key_from_env())

    def health(self) -> dict[str, Any]:
        expired = self.storage.purge_expired_raw()
        cells = self.storage.aggregates()
        published = sum(
            1 for row in cells
            if not aggregation.suppressed_reason(int(row["samples"]),
                                                 len(json.loads(row["contributors"])))
        )
        return {
            "status": "ok",
            "schema_versions": list(schema.SUPPORTED_SCHEMA_VERSIONS),
            "retention_days": retention_days(),
            "minimum_cohort": aggregation.MINIMUM_COHORT,
            "minimum_contributors": aggregation.MINIMUM_CONTRIBUTORS,
            "aggregate_cells": len(cells),
            "published_cells": published,
            "suppressed_cells": len(cells) - published,
            "expired_raw_purged": expired,
            "metrics": self.storage.metrics(),
        }

    # ── helpers ─────────────────────────────────────────────────────────────
    @staticmethod
    def _ok(payload: dict[str, Any], status: int = 200) -> tuple[int, dict[str, str], bytes]:
        return status, {"Content-Type": JSON}, json.dumps(payload, ensure_ascii=False).encode()

    @staticmethod
    def _err(status: int, code: str, detail: str = "") -> tuple[int, dict[str, str], bytes]:
        payload = {"error": code}
        if detail:
            payload["detail"] = security.redact_for_log(detail)
        return status, {"Content-Type": JSON}, json.dumps(payload, ensure_ascii=False).encode()


# ── adaptador HTTP (sólo para ejecutar localmente) ───────────────────────────
def serve(host: str = "127.0.0.1", port: int = 8787, db: str = ":memory:") -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    collector = Collector(Storage(db), token=security.expected_token())

    class Handler(BaseHTTPRequestHandler):
        server_version = "gearbox-collector/ref"

        def _run(self, method: str) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            if length > security.MAX_BODY_BYTES:
                self.send_error(413)
                return
            body = self.rfile.read(length) if length else b""
            status, headers, payload = collector.handle(
                method, self.path.split("?")[0], dict(self.headers), body
            )
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):     # noqa: N802
            self._run("GET")

        def do_POST(self):    # noqa: N802
            self._run("POST")

        def log_message(self, fmt, *args):   # noqa: A003
            # Log operativo sin payload y sin PII: método, ruta y código.
            sys.stderr.write("collector %s\n" % security.redact_for_log(fmt % args))

    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gearbox reference collector")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--db", default="collector.db")
    args = parser.parse_args()
    print(f"⚙ colector de referencia en http://{args.host}:{args.port} (db: {args.db})")
    serve(args.host, args.port, args.db)
