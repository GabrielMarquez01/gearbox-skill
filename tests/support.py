"""Utilidades compartidas por las pruebas. Aísla HOME y carga el núcleo."""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_core():
    """Carga gearbox.py como módulo, respetando el GEARBOX_HOME vigente."""
    spec = importlib.util.spec_from_file_location("gearbox_core", ROOT / "gearbox.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class IsolatedHome(unittest.TestCase):
    """Cada prueba corre en un GEARBOX_HOME propio y desechable."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._saved = {k: os.environ.get(k) for k in (
            "GEARBOX_HOME", "GEARBOX_SKILLS_DIR", "GEARBOX_TELEMETRY_ENDPOINT",
            "GEARBOX_TELEMETRY_TOKEN", "GEARBOX_TELEMETRY_MODE",
            "GEARBOX_TELEMETRY_CONSENT", "GEARBOX_TELEMETRY_DEV",
            "GEARBOX_PRIORS_HMAC_KEY", "GEARBOX_PRIORS_URL",
        )}
        for key in self._saved:
            os.environ.pop(key, None)
        home = Path(self._tmp.name) / "gearbox"
        skills = Path(self._tmp.name) / "skills"
        skills.mkdir(parents=True, exist_ok=True)
        os.environ["GEARBOX_HOME"] = str(home)
        os.environ["GEARBOX_SKILLS_DIR"] = str(skills)
        self.home = home
        # Recargar módulos que resuelven rutas al importarse.
        for name in list(sys.modules):
            if name.startswith("gearboxlib"):
                importlib.reload(sys.modules[name])

    def tearDown(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()


SAMPLE_EVENT = {
    "task_type": "implementation",
    "predicted_gear": "G2",
    "model_family": "sonnet",
    "effort": "high",
    "risk_band": "low",
    "complexity_band": "medium",
    "ambiguity_band": "low",
    "routing_confidence_band": "0.7-0.8",
    "predicted_success_band": "0.8-0.9",
    "outcome": "accepted",
    "rework": False,
    "cost_band": "unknown",
    "latency_band": "unknown",
    "human_override": False,
    "feedback_reason": "none",
}


def sample_capsule(**overrides):
    capsule = {
        "schema_version": "1.0",
        "client_version": "3.0.0",
        "capsule_id": "11111111-2222-4333-8444-555555555555",
        "generated_period": "2026-W30",
        "contribution_mode": "community",
        "events": [dict(SAMPLE_EVENT)],
        "aggregate": {"event_count": 1},
    }
    capsule.update(overrides)
    return capsule


# Secretos FICTICIOS para pruebas negativas. No son credenciales reales.
FAKE_SECRETS = {
    "aws": "AKIAIOSFODNN7EXAMPLE",
    "github": "ghp_0123456789abcdefghijklmnopqrstuvwxyzAB",
    "anthropic": "sk-ant-api03-FAKEfakeFAKEfakeFAKEfake123456",
    "openai": "sk-proj-FAKEfakeFAKEfake0123456789abcdefgh",
    "google": "AIzaSyAFAKEfakeFAKEfakeFAKEfakeFAKEfake1",
    "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----",
    "email": "gabriel.marquez@example.com",
    "unix_path": "/home/usuario/proyectos/cliente-confidencial",
    "windows_path": "C:\\Users\\Gabriel\\secreto.txt",
    "ip": "203.0.113.45",
    "url": "https://intranet.example.com/reporte-privado",
    "card": "4111111111111111",
}
