"""Rutas, permisos restrictivos y escrituras atómicas compartidas.

Regla de seguridad (§18 de la misión): archivos sensibles 0600, directorios 0700,
escrituras atómicas. Todo módulo que toque disco pasa por aquí.
"""
from __future__ import annotations

import json
import os
import secrets
import tempfile
from pathlib import Path
from typing import Any

DIR_MODE = 0o700
FILE_MODE = 0o600


def gb_dir() -> Path:
    """Directorio de datos de Gearbox. Respeta GEARBOX_HOME (usado por tests)."""
    return Path(os.environ.get("GEARBOX_HOME", Path.home() / ".claude" / "gearbox")).expanduser()


def ensure_private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, DIR_MODE)
    except OSError:  # sistemas de archivos sin permisos POSIX (p. ej. algunos montajes)
        pass
    return path


def harden(path: Path) -> Path:
    try:
        os.chmod(path, FILE_MODE)
    except OSError:
        pass
    return path


def atomic_write_text(path: Path, text: str, *, private: bool = True) -> None:
    ensure_private_dir(path.parent) if private else path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        if private:
            os.chmod(tmp, FILE_MODE)
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def atomic_write_json(path: Path, value: Any, *, private: bool = True, indent: int | None = None) -> None:
    atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":")) + "\n",
        private=private,
    )


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return default


def install_salt() -> bytes:
    """Sal local aleatoria, por instalación, nunca transmitida.

    Sirve para derivar seudónimos locales (proyecto, sesión) sin guardar rutas ni
    identificadores originales. Al rotar el contributor_id la sal NO cambia: son
    dominios distintos — ésta jamás sale del equipo.
    """
    path = gb_dir() / ".local_salt"
    raw = None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        raw = None
    if not raw:
        raw = secrets.token_hex(32)
        atomic_write_text(path, raw + "\n")
    return bytes.fromhex(raw)
