import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gearbox_core", ROOT / "gearbox.py")
GB = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GB
assert SPEC.loader is not None
SPEC.loader.exec_module(GB)


class GearboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get("GEARBOX_HOME")
        self.old_skills = os.environ.get("GEARBOX_SKILLS_DIR")
        os.environ["GEARBOX_HOME"] = str(Path(self.tmp.name) / "gearbox")
        os.environ["GEARBOX_SKILLS_DIR"] = str(Path(self.tmp.name) / "skills")
        Path(os.environ["GEARBOX_SKILLS_DIR"]).mkdir(parents=True)

    def tearDown(self):
        if self.old_home is None:
            os.environ.pop("GEARBOX_HOME", None)
        else:
            os.environ["GEARBOX_HOME"] = self.old_home
        if self.old_skills is None:
            os.environ.pop("GEARBOX_SKILLS_DIR", None)
        else:
            os.environ["GEARBOX_SKILLS_DIR"] = self.old_skills
        self.tmp.cleanup()

    def test_routine_routes_to_g0(self):
        route = GB.classify("Busca todas las referencias y formatea la lista")
        self.assertEqual(route.gear, "G0")
        self.assertEqual(route.model, "haiku")
        self.assertFalse(route.human_gate)

    def test_security_routes_to_g4_with_gate(self):
        route = GB.classify("Audita vulnerabilidades OAuth y datos personales")
        self.assertEqual(route.gear, "G4")
        self.assertEqual(route.effort, "xhigh")
        self.assertTrue(route.human_gate)

    def test_system_architecture_routes_to_g5(self):
        route = GB.classify("Diseña la arquitectura completa multi-repo de OpenGravity")
        self.assertEqual(route.gear, "G5")
        self.assertTrue(route.human_gate)

    def test_state_and_jsonl_support_newlines(self):
        value = GB.write_state("G2", "auditar\nrepositorio", "high", "Sonnet")
        raw = (GB.gb_dir() / "state.json").read_text(encoding="utf-8")
        parsed = json.loads(raw)
        self.assertEqual(parsed["task"], "auditar\nrepositorio")
        GB.append_jsonl(GB.gb_dir() / "test.jsonl", {"task": "uno\ndos"})
        lines = (GB.gb_dir() / "test.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["task"], "uno\ndos")
        self.assertEqual(value["gear"], "G2")

    def test_multiline_statusline_payload(self):
        GB.atomic_write_json(GB.gb_dir() / "prices.json", {
            "models": {"sonnet": {"relative": 1}}
        })
        payload = {
            "model": {"display_name": "Claude Sonnet 5"},
            "effort": {"level": "medium"},
            "cost": {"total_cost_usd": 1.234},
            "rate_limits": {
                "five_hour": {"used_percentage": 24},
                "seven_day": {"used_percentage": 61},
            },
        }
        old_stdin = GB.sys.stdin
        try:
            GB.sys.stdin = io.StringIO(json.dumps(payload, indent=2))
            out = io.StringIO()
            with redirect_stdout(out):
                GB.cmd_statusline(None)
        finally:
            GB.sys.stdin = old_stdin
        text = out.getvalue()
        self.assertIn("medium", text)
        self.assertIn("$1.23", text)
        self.assertIn("61% 7d", text)
        self.assertIn("24% 5h", text)

    def test_feedback_updates_local_learning(self):
        route = GB.classify("Implementa un fix pequeño")
        record = GB.record_prediction(route, "Implementa un fix pequeño", "s1", "/tmp/project")
        args = type("Args", (), {"task_id": record["task_id"], "outcome": "accepted"})()
        self.assertEqual(GB.cmd_feedback(args), 0)
        with GB.db_connect() as conn:
            row = conn.execute("SELECT outcome FROM routing_events WHERE task_id=?", (record["task_id"],)).fetchone()
        self.assertEqual(row["outcome"], "accepted")


if __name__ == "__main__":
    unittest.main()
