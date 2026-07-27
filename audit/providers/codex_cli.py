"""Adaptador Codex CLI (familia openai)."""
from __future__ import annotations

from .base import Provider


class CodexCLI(Provider):
    name = "codex"
    vendor_family = "openai"
    binary = "codex"
    # exec + sandbox de sólo lectura: una auditoría no escribe nada.
    args = ("exec", "--sandbox", "read-only")
