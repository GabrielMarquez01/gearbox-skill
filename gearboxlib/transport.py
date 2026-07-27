"""Transporte HTTPS de cápsulas. Sólo se invoca con consentimiento vigente.

Controles (§6 de la misión): TLS validado sin excepciones, HTTP sólo contra
localhost en desarrollo, gzip, tamaño máximo, timeout corto, User-Agent sin
datos del equipo, idempotency key, SHA-256 del cuerpo, versión de schema y
códigos de error estructurados.

El token se lee de ``GEARBOX_TELEMETRY_TOKEN`` y **nunca** se escribe en logs,
mensajes de error ni en la base local.
"""
from __future__ import annotations

import json
import os
import socket
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from . import SCHEMA_VERSION

USER_AGENT = "gearbox-telemetry/3.0 (+https://github.com/GabrielMarquez01/gearbox-skill)"
TIMEOUT_SECONDS = 10
MAX_RESPONSE_BYTES = 64 * 1024
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "[::1]"})

# Códigos de error estructurados (estables, aptos para métricas y pruebas).
ERR_NO_ENDPOINT = "no_endpoint"
ERR_INSECURE_SCHEME = "insecure_scheme"
ERR_TLS = "tls_error"
ERR_TIMEOUT = "timeout"
ERR_NETWORK = "network_error"
ERR_HTTP = "http_error"
ERR_TOO_LARGE = "payload_too_large"
ERR_REJECTED = "rejected_by_collector"
ERR_RATE_LIMITED = "rate_limited"
ERR_UNAUTHORIZED = "unauthorized"
ERR_BAD_RESPONSE = "bad_response"


class InsecureEndpoint(Exception):
    pass


@dataclass(frozen=True)
class Result:
    ok: bool
    code: str
    status: int | None = None
    detail: str = ""
    body: dict[str, Any] | None = None


def validate_endpoint(url: str, *, allow_insecure_localhost: bool | None = None) -> str:
    """Rechaza cualquier destino que no sea HTTPS (salvo localhost en desarrollo)."""
    if not url:
        raise InsecureEndpoint("no hay endpoint configurado")
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return url
    if allow_insecure_localhost is None:
        allow_insecure_localhost = os.environ.get("GEARBOX_TELEMETRY_DEV") == "1"
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "http" and host in LOCAL_HOSTS and allow_insecure_localhost:
        return url
    raise InsecureEndpoint(
        f"endpoint no permitido ({parsed.scheme or 'sin esquema'}): se exige HTTPS "
        "salvo localhost con GEARBOX_TELEMETRY_DEV=1"
    )


def _token() -> str:
    return (os.environ.get("GEARBOX_TELEMETRY_TOKEN") or "").strip()


def build_request(endpoint: str, compressed: bytes, *, capsule_id: str,
                  payload_sha256: str, contributor_id: str = "") -> urllib.request.Request:
    """Arma la petición. Se expone aparte para poder probarla sin red."""
    validate_endpoint(endpoint)
    headers = {
        "Content-Type": "application/json",
        "Content-Encoding": "gzip",
        "User-Agent": USER_AGENT,
        "X-Gearbox-Schema-Version": SCHEMA_VERSION,
        "X-Gearbox-Content-Sha256": payload_sha256,
        "Idempotency-Key": capsule_id,
        "Accept": "application/json",
    }
    if contributor_id:
        headers["X-Gearbox-Contributor"] = contributor_id
    token = _token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(endpoint, data=compressed, headers=headers, method="POST")


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def send(endpoint: str, compressed: bytes, *, capsule_id: str, payload_sha256: str,
         contributor_id: str = "", timeout: int = TIMEOUT_SECONDS) -> Result:
    """Envía una cápsula. Nunca lanza: devuelve un Result con código estable."""
    if len(compressed) > 1024 * 1024:
        return Result(False, ERR_TOO_LARGE, detail=f"{len(compressed)} bytes")
    try:
        request = build_request(
            endpoint, compressed, capsule_id=capsule_id,
            payload_sha256=payload_sha256, contributor_id=contributor_id,
        )
    except InsecureEndpoint as exc:
        return Result(False, ERR_INSECURE_SCHEME, detail=str(exc))

    context = _ssl_context() if urlparse(endpoint).scheme == "https" else None
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            raw = response.read(MAX_RESPONSE_BYTES)
            status = int(getattr(response, "status", 0) or 0)
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        code = {
            401: ERR_UNAUTHORIZED, 403: ERR_UNAUTHORIZED,
            409: ERR_REJECTED, 413: ERR_TOO_LARGE, 422: ERR_REJECTED,
            429: ERR_RATE_LIMITED,
        }.get(status, ERR_HTTP)
        # El cuerpo del error puede traer detalle del colector; se acota y no se
        # registra el token bajo ninguna circunstancia.
        try:
            detail = exc.read(2048).decode("utf-8", errors="replace")[:500]
        except OSError:
            detail = ""
        return Result(False, code, status=status, detail=_redact(detail))
    except ssl.SSLError as exc:
        return Result(False, ERR_TLS, detail=_redact(str(exc)))
    except socket.timeout:
        return Result(False, ERR_TIMEOUT)
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", "")
        if isinstance(reason, ssl.SSLError) or "CERTIFICATE" in str(reason).upper():
            return Result(False, ERR_TLS, detail=_redact(str(reason)))
        if isinstance(reason, socket.timeout):
            return Result(False, ERR_TIMEOUT)
        return Result(False, ERR_NETWORK, detail=_redact(str(reason)))
    except (OSError, ValueError) as exc:
        return Result(False, ERR_NETWORK, detail=_redact(str(exc)))

    body: dict[str, Any] | None = None
    if raw:
        try:
            parsed = json.loads(raw.decode("utf-8", errors="replace"))
            body = parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = None
    if 200 <= status < 300:
        return Result(True, "ok", status=status, body=body)
    return Result(False, ERR_BAD_RESPONSE, status=status, body=body)


def _redact(text: str) -> str:
    """Última barrera: si un token se coló en un mensaje, no se propaga."""
    token = _token()
    if token and token in text:
        text = text.replace(token, "«token-redactado»")
    return text.replace("Bearer ", "Bearer «redactado» ")
