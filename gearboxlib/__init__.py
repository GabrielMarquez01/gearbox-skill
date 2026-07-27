"""Gearbox V3 support library — stdlib only.

Se distribuye junto a ``gearbox.py`` y se instala en ``~/.claude/gearbox/``.
Cada módulo tiene una responsabilidad estrecha y auditable:

``privacy``    detección de secretos/PII, generalización a bandas, allowlist
``consent``    registro de consentimiento explícito y revocable
``capsule``    construcción de la cápsula de telemetría minimizada
``outbox``     cola transaccional local con reintentos
``transport``  envío HTTPS (nunca se invoca sin consentimiento vigente)
``priors``     cliente de priors comunitarios agregados
``paths``      rutas y permisos restrictivos compartidos
"""

__all__ = [
    "privacy",
    "consent",
    "capsule",
    "outbox",
    "transport",
    "priors",
    "paths",
]

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "1.0"
