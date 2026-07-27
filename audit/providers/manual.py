"""Adaptador manual: dos respuestas pegadas a mano, sin ejecutar ningún CLI.

Existe porque la auditoría cruzada no puede depender de que haya CLIs instalados
y autenticados (§18). Con este adaptador, una persona pega la respuesta que
obtuvo de cada proveedor —en la web, en otra máquina, donde sea— y el resto del
pipeline (comparación ciega, jerarquía de fuentes, brief, gate humano) funciona
igual.

Es también el camino de prueba: permite verificar la orquestación sin red.
"""
from __future__ import annotations

from pathlib import Path

from ..contracts import Capability, ProviderResponse, Role
from .base import Provider, parse_claims


class ManualProvider(Provider):
    name = "manual"
    vendor_family = "human"
    binary = ""

    def __init__(self, text: str = "", *, vendor_family: str = "human",
                 label: str = "manual"):
        self.text = text
        self.vendor_family = vendor_family
        self.name = label

    @classmethod
    def from_file(cls, path: str | Path, *, vendor_family: str, label: str) -> "ManualProvider":
        content = Path(path).read_text(encoding="utf-8")
        return cls(content, vendor_family=vendor_family, label=label)

    def capability(self) -> Capability:
        return Capability.AVAILABLE if self.text.strip() else Capability.UNAVAILABLE

    def run(self, prompt: str, role: Role, *, timeout: int = 0) -> ProviderResponse:
        if not self.text.strip():
            return ProviderResponse(self.name, self.vendor_family, role,
                                    capability=Capability.UNAVAILABLE,
                                    error="respuesta manual vacía")
        claims, confidence = parse_claims(self.text)
        return ProviderResponse(
            provider=self.name, vendor_family=self.vendor_family, role=role,
            answer=self.text, claims=claims, confidence=confidence,
        )
