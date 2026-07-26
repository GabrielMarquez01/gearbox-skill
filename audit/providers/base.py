"""Base de los adaptadores de proveedor.

Reglas duras para cualquier adaptador:

* **Nunca** leer, copiar ni inspeccionar archivos de autenticación del
  proveedor. Si el CLI no está autenticado, se reporta ``UNAUTHENTICATED`` y se
  acaba ahí: el usuario autentica personalmente, cada quien con su cuenta.
* ``subprocess`` con **lista de argumentos**, jamás ``shell=True`` ni
  concatenación de prompts en una línea de comando.
* El prompt viaja por **stdin**, no por argv: no aparece en ``ps`` ni en el
  historial del shell.
* Timeout obligatorio y salida acotada.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any

from ..contracts import Capability, Claim, ClaimType, ProviderResponse, Role, Source, SourceTier

DEFAULT_TIMEOUT = 180
MAX_OUTPUT_CHARS = 40_000


class Provider:
    """Adaptador de un motor. Subclasear y declarar ``name``/``vendor_family``."""

    name = "base"
    vendor_family = "otro"
    binary = ""
    args: tuple[str, ...] = ()

    def capability(self) -> Capability:
        if not self.binary:
            return Capability.UNSUPPORTED
        if shutil.which(self.binary) is None:
            return Capability.UNAVAILABLE
        return Capability.AVAILABLE

    def run(self, prompt: str, role: Role, *, timeout: int = DEFAULT_TIMEOUT) -> ProviderResponse:
        capability = self.capability()
        if capability != Capability.AVAILABLE:
            return ProviderResponse(
                provider=self.name, vendor_family=self.vendor_family, role=role,
                capability=capability,
                error=f"{self.name}: {capability.value}",
            )
        try:
            completed = subprocess.run(          # noqa: S603 — lista de args, sin shell
                [self.binary, *self.args],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
                env=self._env(),
            )
        except subprocess.TimeoutExpired:
            return ProviderResponse(self.name, self.vendor_family, role,
                                    error="timeout", capability=Capability.AVAILABLE)
        except (OSError, ValueError) as exc:
            return ProviderResponse(self.name, self.vendor_family, role,
                                    error=f"{type(exc).__name__}", capability=Capability.UNAVAILABLE)

        output = completed.stdout or ""
        truncated = len(output) > MAX_OUTPUT_CHARS
        output = output[:MAX_OUTPUT_CHARS]
        if completed.returncode != 0:
            stderr = (completed.stderr or "")[:400]
            capability = (Capability.UNAUTHENTICATED
                          if re.search(r"(?i)auth|login|unauthorized|not signed", stderr)
                          else Capability.AVAILABLE)
            return ProviderResponse(self.name, self.vendor_family, role,
                                    error=f"exit {completed.returncode}: {stderr}",
                                    capability=capability)
        return self.parse(output, role, truncated=truncated)

    def _env(self) -> dict[str, str]:
        """Entorno mínimo. No se inyectan credenciales: cada CLI usa la sesión
        que su dueño ya autenticó."""
        keep = ("PATH", "HOME", "LANG", "LC_ALL", "TERM", "USER", "SHELL")
        return {k: v for k, v in os.environ.items() if k in keep}

    def parse(self, output: str, role: Role, *, truncated: bool = False) -> ProviderResponse:
        claims, confidence = parse_claims(output)
        return ProviderResponse(
            provider=self.name, vendor_family=self.vendor_family, role=role,
            answer=output, claims=claims, confidence=confidence, truncated=truncated,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Extracción de afirmaciones y fuentes desde texto libre del proveedor
# ─────────────────────────────────────────────────────────────────────────────
CLAIM_MARKERS: tuple[tuple[str, ClaimType], ...] = (
    ("hecho confirmado", ClaimType.CONFIRMED_FACT),
    ("confirmed fact", ClaimType.CONFIRMED_FACT),
    ("inferencia", ClaimType.INFERENCE),
    ("inference", ClaimType.INFERENCE),
    ("supuesto", ClaimType.ASSUMPTION),
    ("assumption", ClaimType.ASSUMPTION),
    ("opinión técnica", ClaimType.TECHNICAL_OPINION),
    ("opinion tecnica", ClaimType.TECHNICAL_OPINION),
    ("recomendación", ClaimType.RECOMMENDATION),
    ("recommendation", ClaimType.RECOMMENDATION),
    ("incertidumbre", ClaimType.UNCERTAINTY),
    ("uncertainty", ClaimType.UNCERTAINTY),
)

URL_RE = re.compile(r"https?://[^\s\)\]]+")
NORM_RE = re.compile(
    r"(?i)\b(?:art[íi]culo|art\.|regla|ley|reglamento|nom|dof|"
    r"regulation|article|recital|§)\s*[\w\.\-/]+"
)
CONFIDENCE_RE = re.compile(r"(?i)confianza[^0-9]{0,12}(\d{1,3})\s*%|confidence[^0-9]{0,12}(\d{1,3})\s*%")


def classify_source(identifier: str) -> SourceTier:
    """Clasificación conservadora. Ante la duda, se degrada el nivel.

    Sesgo explícito: un dominio gubernamental o de organismo oficial es A;
    tribunales/academia es B; lo demás baja a D salvo señal clara.
    """
    lowered = identifier.lower()
    if re.search(r"\.gob\.|\.gov(\.|/|$)|europa\.eu|eur-lex|diputados\.gob|dof\.gob|"
                 r"boe\.es|legislation\.gov", lowered):
        return SourceTier.A
    if re.search(r"(?i)^(?:art[íi]culo|art\.|regla|ley|reglamento|dof|nom|article|§)", identifier):
        return SourceTier.A
    if re.search(r"\.edu(\.|/|$)|scj|tribunal|court|iso\.org|ietf\.org|w3\.org|nist\.gov",
                 lowered):
        return SourceTier.B
    return SourceTier.D


def parse_claims(output: str) -> tuple[tuple[Claim, ...], float]:
    """Convierte la respuesta en afirmaciones tipadas.

    Es intencionalmente literal: sólo reconoce lo que el proveedor marcó. Un
    texto sin marcas produce una única afirmación de tipo *opinión técnica* con
    confianza baja — que es exactamente lo que merece.
    """
    claims: list[Claim] = []
    for raw_line in output.splitlines():
        line = raw_line.strip(" -*\t")
        if not line:
            continue
        lowered = line.lower()
        claim_type = next((t for marker, t in CLAIM_MARKERS if lowered.startswith(marker)), None)
        if claim_type is None:
            continue
        sources: list[Source] = []
        for url in URL_RE.findall(line):
            sources.append(Source(classify_source(url), url, accessed=False))
        for norm in NORM_RE.findall(line):
            sources.append(Source(classify_source(norm), norm.strip(), accessed=False))
        confidence = 0.75 if claim_type == ClaimType.CONFIRMED_FACT and sources else 0.5
        claims.append(Claim(text=line, claim_type=claim_type,
                            sources=tuple(sources), confidence=confidence))

    if not claims and output.strip():
        claims.append(Claim(
            text=output.strip()[:400],
            claim_type=ClaimType.TECHNICAL_OPINION,
            sources=tuple(Source(classify_source(u), u) for u in URL_RE.findall(output)[:5]),
            confidence=0.35,
        ))

    match = CONFIDENCE_RE.search(output)
    if match:
        raw = match.group(1) or match.group(2)
        declared = max(0.0, min(1.0, int(raw) / 100.0))
    else:
        declared = sum(c.confidence for c in claims) / len(claims) if claims else 0.0
    return tuple(claims), declared


def describe(provider: Provider) -> dict[str, Any]:
    return {
        "name": provider.name,
        "vendor_family": provider.vendor_family,
        "binary": provider.binary,
        "capability": provider.capability().value,
    }
