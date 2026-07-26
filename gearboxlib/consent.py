"""Consentimiento explícito, verificable y revocable.

Reglas duras:

* El modo por defecto es ``local``: cero transmisión, cero red.
* ``community`` y ``self-hosted`` exigen un registro de consentimiento vigente.
* Nada de casillas premarcadas: el consentimiento se otorga con un acto
  explícito (comando o respuesta afirmativa), nunca por omisión.
* Revocar invalida el consentimiento, vacía la cola, rota el seudónimo y deja
  un comprobante local.
"""
from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import POLICY_VERSION, SCHEMA_VERSION
from .paths import atomic_write_json, gb_dir, read_json

MODE_LOCAL = "local"
MODE_COMMUNITY = "community"
MODE_SELF_HOSTED = "self-hosted"
VALID_MODES = (MODE_LOCAL, MODE_COMMUNITY, MODE_SELF_HOSTED)

STATUS_NONE = "none"
STATUS_GRANTED = "granted"
STATUS_REVOKED = "revoked"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def consent_path() -> Path:
    return gb_dir() / "consent.json"


def receipts_path() -> Path:
    return gb_dir() / "consent-receipts.jsonl"


def default_record() -> dict[str, Any]:
    return {
        "status": STATUS_NONE,
        "mode": MODE_LOCAL,
        "policy_version": POLICY_VERSION,
        "schema_version": SCHEMA_VERSION,
        "granted_at": None,
        "source": None,
        "contributor_id": None,
        "endpoint": None,
    }


def load() -> dict[str, Any]:
    record = read_json(consent_path(), None)
    if not isinstance(record, dict):
        return default_record()
    merged = default_record()
    merged.update({k: v for k, v in record.items() if k in merged})
    if merged.get("mode") not in VALID_MODES:
        merged["mode"] = MODE_LOCAL
    if merged.get("status") not in (STATUS_NONE, STATUS_GRANTED, STATUS_REVOKED):
        merged["status"] = STATUS_NONE
    return merged


def save(record: dict[str, Any]) -> dict[str, Any]:
    atomic_write_json(consent_path(), record, indent=2)
    return record


def _receipt(kind: str, record: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    entry = {
        "receipt_id": str(uuid.uuid4()),
        "kind": kind,
        "at": _now(),
        "mode": record.get("mode"),
        "status": record.get("status"),
        "policy_version": record.get("policy_version"),
        "schema_version": record.get("schema_version"),
    }
    if extra:
        entry.update(extra)
    path = receipts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        import json as _json

        fh.write(_json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return entry


def new_contributor_id() -> str:
    """Seudónimo aleatorio. No deriva de equipo, correo, IP ni ruta."""
    return str(uuid.UUID(bytes=secrets.token_bytes(16), version=4))


def is_active() -> bool:
    """¿Hay consentimiento vigente para transmitir?"""
    record = load()
    return (
        record.get("status") == STATUS_GRANTED
        and record.get("mode") in (MODE_COMMUNITY, MODE_SELF_HOSTED)
        and bool(record.get("contributor_id"))
    )


def grant(mode: str, source: str = "cli", endpoint: str | None = None) -> dict[str, Any]:
    if mode not in (MODE_COMMUNITY, MODE_SELF_HOSTED):
        raise ValueError(f"modo no consentible: {mode}")
    if mode == MODE_SELF_HOSTED and not endpoint:
        raise ValueError("self-hosted requiere --endpoint")
    record = load()
    record.update({
        "status": STATUS_GRANTED,
        "mode": mode,
        "policy_version": POLICY_VERSION,
        "schema_version": SCHEMA_VERSION,
        "granted_at": _now(),
        "source": source,
        "contributor_id": record.get("contributor_id") or new_contributor_id(),
        "endpoint": endpoint,
    })
    save(record)
    _receipt("granted", record)
    return record


def disable() -> dict[str, Any]:
    """Detiene transmisiones futuras. NO borra la cola ni el consentimiento."""
    record = load()
    record["mode"] = MODE_LOCAL
    save(record)
    _receipt("disabled", record)
    return record


def revoke() -> dict[str, Any]:
    """Invalida el consentimiento y rota el seudónimo.

    El vaciado de la cola lo ejecuta el llamador (outbox.purge_all) porque este
    módulo no debe conocer el almacenamiento; el comando ``telemetry revoke``
    encadena ambos y deja constancia del conteo eliminado.
    """
    record = load()
    previous = record.get("contributor_id")
    record.update({
        "status": STATUS_REVOKED,
        "mode": MODE_LOCAL,
        "granted_at": None,
        "source": None,
        "contributor_id": None,
        "endpoint": None,
    })
    save(record)
    _receipt("revoked", record, {"previous_contributor_id": previous})
    return record


def rotate_id() -> str:
    record = load()
    if record.get("status") != STATUS_GRANTED:
        raise ValueError("no hay consentimiento vigente que rotar")
    old = record.get("contributor_id")
    record["contributor_id"] = new_contributor_id()
    save(record)
    _receipt("rotated", record, {"previous_contributor_id": old})
    return record["contributor_id"]


# ─────────────────────────────────────────────────────────────────────────────
# Instalación no interactiva
# ─────────────────────────────────────────────────────────────────────────────
def bootstrap_from_env(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Aplica el consentimiento en instalaciones desatendidas.

    Se queda en ``local`` salvo que existan LAS DOS variables. Una sola no basta:
    declarar el modo no equivale a consentir.
    """
    env = os.environ if env is None else env
    mode = (env.get("GEARBOX_TELEMETRY_MODE") or "").strip().lower()
    consented = (env.get("GEARBOX_TELEMETRY_CONSENT") or "").strip().lower() == "yes"
    endpoint = (env.get("GEARBOX_TELEMETRY_ENDPOINT") or "").strip() or None

    if mode in (MODE_COMMUNITY, MODE_SELF_HOSTED) and consented:
        try:
            return grant(mode, source="env", endpoint=endpoint)
        except ValueError:
            return load()
    record = load()
    if record.get("status") == STATUS_NONE:
        save(record)
    return record


EXPLAIN = """\
Gearbox funciona completamente en modo local.

Modo actual: {mode} (estado de consentimiento: {status})

Qué SÍ se envía si activas Community Learning:
  · tipo de tarea, marcha predicha, familia de modelo y esfuerzo;
  · bandas de riesgo, complejidad, ambigüedad y confianza (rangos, no cifras);
  · resultado (aceptado/rechazado/retrabajo) y si hubo intervención humana;
  · el periodo en semanas — nunca la hora exacta de cada tarea.

Qué NUNCA se envía:
  · prompts, respuestas, código, archivos ni fragmentos de documentos;
  · rutas, nombres de repositorio, rama, commit ni nombres de proyecto;
  · usuario, host, correo, teléfono, IP, tokens, llaves ni cookies;
  · identificadores de sesión, task_id locales ni hashes de prompts;
  · texto libre de ningún tipo.

Controles a tu disposición:
  gearbox.py telemetry preview   ver exactamente el paquete antes de enviarlo
  gearbox.py telemetry export    guardar el paquete a disco para revisarlo
  gearbox.py telemetry disable   detener envíos futuros
  gearbox.py telemetry revoke    invalidar consentimiento y borrar la cola
  gearbox.py telemetry purge     vaciar la cola local

La licencia MIT no depende de que envíes datos. Puedes usar el modo local para
siempre, o apuntar a tu propio colector con `telemetry enable self-hosted`.
"""

PROMPT = """\
Gearbox funciona completamente en modo local.
Puedes participar voluntariamente en Community Learning:
- se envían métricas agregadas de routing y resultados;
- no se envían prompts, respuestas, código, nombres ni rutas;
- puedes revisar cada paquete;
- puedes desactivarlo y eliminar la cola local.
Selecciona:
1. Local únicamente
2. Community Learning
3. Configurar colector propio
"""
