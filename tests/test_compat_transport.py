"""Compatibilidad con V2, transporte y la promesa central: local = cero red."""
from __future__ import annotations

import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from support import ROOT, IsolatedHome, load_core, sample_capsule

from gearboxlib import consent, outbox, transport


class NoNetworkGuard:
    """Bloquea cualquier intento de abrir un socket y lo delata."""

    def __enter__(self):
        self.attempts: list = []
        self._socket = socket.socket
        self._create = socket.create_connection
        self._getaddr = socket.getaddrinfo
        guard = self

        def deny(*args, **kwargs):
            guard.attempts.append(args)
            raise AssertionError("se intentó abrir una conexión de red")

        socket.socket = deny
        socket.create_connection = deny
        socket.getaddrinfo = deny
        return self

    def __exit__(self, *exc):
        socket.socket = self._socket
        socket.create_connection = self._create
        socket.getaddrinfo = self._getaddr
        return False


class LocalModeIsOfflineTests(IsolatedHome):
    def test_classify_record_and_feedback_make_zero_connections(self):
        core = load_core()
        with NoNetworkGuard() as guard:
            route = core.classify("Implementa el módulo de reportes")
            record = core.record_prediction(route, "Implementa el módulo", "s", "/tmp/p")
            args = type("A", (), {"task_id": record["task_id"], "outcome": "accepted",
                                  "rating": None, "reason": None})()
            core.cmd_feedback(args)
            core.cmd_history(type("A", (), {"limit": 5})())
        self.assertEqual(guard.attempts, [])

    def test_hook_makes_zero_connections(self):
        core = load_core()
        payload = json.dumps({"prompt": "Arregla el bug del login",
                              "session_id": "s1", "cwd": "/tmp/proyecto"})
        with NoNetworkGuard() as guard:
            old_stdin = core.sys.stdin
            try:
                core.sys.stdin = io.StringIO(payload)
                out = io.StringIO()
                with redirect_stdout(out):
                    core.cmd_hook(None)
            finally:
                core.sys.stdin = old_stdin
        self.assertEqual(guard.attempts, [])
        self.assertIn("GEARBOX V3 PREDICTION", out.getvalue())

    def test_send_without_consent_refuses_before_touching_the_network(self):
        core = load_core()
        os.environ["GEARBOX_TELEMETRY_ENDPOINT"] = "https://ejemplo.invalid/v1/capsules"
        args = type("A", (), {"action": "send", "mode": None, "endpoint": None,
                              "out": None, "yes": True})()
        with NoNetworkGuard() as guard:
            err = io.StringIO()
            old = core.sys.stderr
            try:
                core.sys.stderr = err
                code = core.cmd_telemetry(args)
            finally:
                core.sys.stderr = old
        self.assertEqual(code, 1)
        self.assertEqual(guard.attempts, [])
        self.assertIn("Sin consentimiento", err.getvalue())

    def test_revoke_deletes_the_pending_queue(self):
        core = load_core()
        consent.grant("community")
        outbox.enqueue(sample_capsule(), "1.0")
        self.assertEqual(outbox.stats()["pending"], 1)
        out = io.StringIO()
        with redirect_stdout(out):
            core.cmd_telemetry(type("A", (), {"action": "revoke"})())
        self.assertEqual(outbox.stats()["pending"], 0)
        self.assertFalse(consent.is_active())
        self.assertIn("queued_capsules_deleted", out.getvalue())


class TransportTests(unittest.TestCase):
    def test_http_is_refused(self):
        with self.assertRaises(transport.InsecureEndpoint):
            transport.validate_endpoint("http://colector.example.com/v1/capsules")

    def test_localhost_http_only_in_dev_mode(self):
        with self.assertRaises(transport.InsecureEndpoint):
            transport.validate_endpoint("http://127.0.0.1:8787/v1/capsules",
                                        allow_insecure_localhost=False)
        self.assertTrue(transport.validate_endpoint("http://127.0.0.1:8787/v1/capsules",
                                                    allow_insecure_localhost=True))

    def test_https_is_accepted(self):
        self.assertTrue(transport.validate_endpoint("https://colector.example.com/v1"))

    def test_empty_endpoint_is_refused(self):
        with self.assertRaises(transport.InsecureEndpoint):
            transport.validate_endpoint("")

    def test_request_headers_carry_contract_metadata(self):
        request = transport.build_request(
            "https://colector.example.com/v1/capsules", b"gz",
            capsule_id="abc", payload_sha256="deadbeef", contributor_id="pseudo-1")
        self.assertEqual(request.get_header("Content-encoding"), "gzip")
        self.assertEqual(request.get_header("Idempotency-key"), "abc")
        self.assertEqual(request.get_header("X-gearbox-content-sha256"), "deadbeef")
        self.assertEqual(request.get_header("X-gearbox-contributor"), "pseudo-1")

    def test_user_agent_has_no_device_information(self):
        agent = transport.USER_AGENT
        for leak in (os.uname().nodename, os.path.expanduser("~"), sys.platform):
            self.assertNotIn(leak, agent)

    def test_token_comes_from_env_and_is_never_echoed(self):
        os.environ["GEARBOX_TELEMETRY_TOKEN"] = "token-super-secreto"
        try:
            request = transport.build_request(
                "https://colector.example.com/v1", b"x",
                capsule_id="a", payload_sha256="b")
            self.assertIn("token-super-secreto", request.get_header("Authorization"))
            redacted = transport._redact("falló con token-super-secreto adentro")
            self.assertNotIn("token-super-secreto", redacted)
        finally:
            os.environ.pop("GEARBOX_TELEMETRY_TOKEN", None)

    def test_send_returns_structured_code_on_insecure_endpoint(self):
        result = transport.send("http://malo.example.com", b"x",
                                capsule_id="a", payload_sha256="b")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, transport.ERR_INSECURE_SCHEME)


class V2CompatibilityTests(IsolatedHome):
    """Los comandos históricos deben seguir funcionando igual."""

    def run_wrapper(self, script: str, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["GEARBOX_HOME"] = str(self.home)
        self.home.mkdir(parents=True, exist_ok=True)
        for name in ("gearbox.py",):
            (self.home / name).write_bytes((ROOT / name).read_bytes())
        target = self.home / "gearboxlib"
        if not target.exists():
            target.mkdir()
            for item in (ROOT / "gearboxlib").glob("*.py"):
                (target / item.name).write_bytes(item.read_bytes())
        return subprocess.run(
            ["bash", str(ROOT / script), *args],
            capture_output=True, text=True, env=env, timeout=60,
        )

    def test_set_sh_still_works(self):
        result = self.run_wrapper("set.sh", "G2", "ejecución", "high")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("G2", result.stdout)
        state = json.loads((self.home / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["gear"], "G2")
        self.assertEqual(state["task"], "ejecución")

    def test_reset_sh_still_works(self):
        self.run_wrapper("set.sh", "G4", "crítico", "xhigh")
        result = self.run_wrapper("reset.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((self.home / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["gear"], "auto")

    def test_log_sh_decision_still_appends(self):
        result = self.run_wrapper("log.sh", "decision", "G2", "G2", "fix checkout", "supabase")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = (self.home / "decisions.jsonl").read_text(encoding="utf-8").strip().splitlines()
        entry = json.loads(lines[-1])
        self.assertEqual(entry["gear_actual"], "G2")
        self.assertEqual(entry["task"], "fix checkout")

    def test_invalid_gear_is_still_rejected(self):
        result = self.run_wrapper("set.sh", "G9")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inválida", result.stderr)

    def test_statusline_renders_with_gears_and_usage(self):
        core = load_core()
        payload = {
            "model": {"display_name": "Claude Sonnet 5"},
            "effort": {"level": "medium"},
            "cost": {"total_cost_usd": 1.234},
            "rate_limits": {"five_hour": {"used_percentage": 24},
                            "seven_day": {"used_percentage": 61}},
        }
        old = core.sys.stdin
        try:
            core.sys.stdin = io.StringIO(json.dumps(payload))
            out = io.StringIO()
            with redirect_stdout(out):
                core.cmd_statusline(None)
        finally:
            core.sys.stdin = old
        text = out.getvalue()
        for expected in ("medium", "$1.23", "61% 7d", "24% 5h"):
            self.assertIn(expected, text)

    def test_gear_table_g0_to_g5_is_intact(self):
        core = load_core()
        for gear in ("G0", "G1", "G2", "G3", "G4", "G5"):
            self.assertIn(gear, core.VALID_GEARS)
            self.assertIn(gear, core.DEFAULT_ROUTES)
            self.assertIn(gear, core.DEFAULT_TASKS)

    def test_observe_mode_is_still_the_default(self):
        core = load_core()
        self.assertEqual(core.default_policy()["mode"], "observe")

    def test_human_gate_categories_are_preserved(self):
        core = load_core()
        categories = core.default_policy()["human_gate_categories"]
        for required in ("security", "privacy", "payments", "production", "legal",
                         "deletion", "irreversible"):
            self.assertIn(required, categories)

    def test_automation_never_allows_g3_or_above(self):
        core = load_core()
        allowed = core.default_policy()["automation"]["allowed_gears"]
        for forbidden in ("G3", "G3.5", "G4", "G5"):
            self.assertNotIn(forbidden, allowed)


class InstallerTests(unittest.TestCase):
    """Instalación limpia, reinstalación y desinstalación sin daño colateral."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.claude = Path(self.tmp.name) / ".claude"
        self.claude.mkdir(parents=True)
        self.env = dict(os.environ)
        self.env["CLAUDE_DIR"] = str(self.claude)
        self.env["HOME"] = self.tmp.name
        self.env.pop("GEARBOX_HOME", None)

    def tearDown(self):
        self.tmp.cleanup()

    def install(self) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(ROOT / "install.sh")],
                              capture_output=True, text=True, env=self.env,
                              cwd=str(ROOT), timeout=180)

    def test_clean_install_then_reinstall_is_idempotent(self):
        first = self.install()
        self.assertEqual(first.returncode, 0, first.stderr)
        settings = json.loads((self.claude / "settings.json").read_text(encoding="utf-8"))
        hooks_before = json.dumps(settings["hooks"], sort_keys=True)

        second = self.install()
        self.assertEqual(second.returncode, 0, second.stderr)
        settings = json.loads((self.claude / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(json.dumps(settings["hooks"], sort_keys=True), hooks_before)

    def test_install_defaults_to_local_without_consent(self):
        self.install()
        record = json.loads((self.claude / "gearbox" / "consent.json").read_text(encoding="utf-8"))
        self.assertEqual(record["mode"], "local")
        self.assertNotEqual(record["status"], "granted")

    def test_env_mode_alone_does_not_enable_telemetry_on_install(self):
        self.env["GEARBOX_TELEMETRY_MODE"] = "community"
        self.install()
        record = json.loads((self.claude / "gearbox" / "consent.json").read_text(encoding="utf-8"))
        self.assertNotEqual(record["status"], "granted")

    def test_backup_of_previous_settings_is_kept(self):
        (self.claude / "settings.json").write_text(
            json.dumps({"statusLine": {"type": "command", "command": "mi-statusline"},
                        "model": "sonnet"}), encoding="utf-8")
        self.install()
        backup = self.claude / "backups" / "gearbox" / "settings.pre-gearbox.json"
        self.assertTrue(backup.exists())
        self.assertIn("mi-statusline", backup.read_text(encoding="utf-8"))

    def test_foreign_statusline_is_not_replaced(self):
        (self.claude / "settings.json").write_text(
            json.dumps({"statusLine": {"type": "command", "command": "mi-statusline"}}),
            encoding="utf-8")
        self.install()
        settings = json.loads((self.claude / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["statusLine"]["command"], "mi-statusline")

    def test_uninstall_preserves_foreign_settings_and_archives_data(self):
        (self.claude / "settings.json").write_text(
            json.dumps({"model": "sonnet", "permissions": {"allow": ["Bash(ls:*)"]},
                        "hooks": {"SessionStart": [{"hooks": [{"type": "command",
                                                               "command": "otro-script"}]}]}}),
            encoding="utf-8")
        self.install()
        result = subprocess.run(["bash", str(self.claude / "gearbox" / "uninstall.sh")],
                                capture_output=True, text=True, env=self.env, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = json.loads((self.claude / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["permissions"]["allow"], ["Bash(ls:*)"])
        self.assertIn("otro-script", json.dumps(settings))
        self.assertNotIn("statusLine", settings)
        archived = list((self.claude / "backups" / "gearbox").glob("uninstalled-*"))
        self.assertTrue(archived, "los datos deben archivarse, no borrarse")

    def test_uninstall_removes_the_managed_claude_md_block(self):
        self.install()
        subprocess.run(["bash", str(self.claude / "gearbox" / "uninstall.sh")],
                       capture_output=True, text=True, env=self.env, timeout=60)
        text = (self.claude / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertNotIn("GEARBOX:START", text)


if __name__ == "__main__":
    unittest.main()
