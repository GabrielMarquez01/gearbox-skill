"""Adaptador Gemini/Antigravity CLI (familia google)."""
from __future__ import annotations

from .base import Provider


class GeminiCLI(Provider):
    name = "gemini"
    vendor_family = "google"
    binary = "gemini"
    args = ("-p",)
