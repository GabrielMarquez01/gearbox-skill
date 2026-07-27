"""Adaptadores de proveedor. Ninguno se asume instalado ni autenticado."""
from __future__ import annotations

from .base import Provider, describe
from .claude_cli import ClaudeCLI
from .codex_cli import CodexCLI
from .gemini_cli import GeminiCLI
from .manual import ManualProvider

REGISTRY: dict[str, type[Provider]] = {
    "claude": ClaudeCLI,
    "codex": CodexCLI,
    "gemini": GeminiCLI,
    "manual": ManualProvider,
}


def available() -> list[dict]:
    """Inventario de capacidades. Se reporta tal cual: available, unavailable,
    unauthenticated o unsupported. Nunca se infiere disponibilidad."""
    return [describe(cls()) for name, cls in REGISTRY.items() if name != "manual"]


__all__ = ["Provider", "ClaudeCLI", "CodexCLI", "GeminiCLI", "ManualProvider",
           "REGISTRY", "available", "describe"]
