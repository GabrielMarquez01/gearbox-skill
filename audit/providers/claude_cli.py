"""Adaptador Claude Code CLI (familia anthropic)."""
from __future__ import annotations

from .base import Provider


class ClaudeCLI(Provider):
    name = "claude"
    vendor_family = "anthropic"
    binary = "claude"
    # -p: modo no interactivo. El prompt entra por stdin, nunca por argv.
    args = ("-p",)
