"""Consentimiento, cápsula y cola de salida.

Lo que se demuestra aquí: sin consentimiento no sale nada, la vista previa es
exactamente lo que se enviaría, y la cola no duplica ni pierde en silencio.
"""
from __future__ import annotations

import gzip
import json
import unittest
from datetime import datetime, timedelta, timezone

import sys as _sys
from pathlib import Path as _Path
# Permite invocar tanto `unittest discover -s tests` como
# `unittest tests.test_x`: en el segundo caso este directorio no queda
# en sys.path y `support` no se encontraría.
_sys.path.insert(0, str(_Path(__file__).resolve().parent))

from support import FAKE_SECRETS, IsolatedHome, load_core, sample_capsule

from gearboxlib import capsule as gb_capsule
from gearboxlib import consent, outbox, privacy


class ConsentTests(IsolatedHome):
    def test_default_is_local_and_inactive(self):
        record = consent.load()
        self.assertEqual(record["mode"], consent.MODE_LOCAL)
        self.assertEqual(record["status"], consent.STATUS_NONE)
        self.assertFalse(consent.is_active())

    def test_nothing_is_pre_checked(self):
        """No hay ruta que active telemetría sin un acto explícito."""
        record = consent.bootstrap_from_env({})
        self.assertEqual(record["mode"], consent.MODE_LOCAL)
        self.assertFalse(consent.is_active())

    def test_mode_env_alone_does_not_grant_consent(self):
        consent.bootstrap_from_env({"GEARBOX_TELEMETRY_MODE": "community"})
        self.assertFalse(consent.is_active())

    def test_consent_env_alone_does_not_grant_consent(self):
        consent.bootstrap_from_env({"GEARBOX_TELEMETRY_CONSENT": "yes"})
        self.assertFalse(consent.is_active())

    def test_both_env_vars_required_to_grant(self):
        consent.bootstrap_from_env({
            "GEARBOX_TELEMETRY_MODE": "community",
            "GEARBOX_TELEMETRY_CONSENT": "yes",
        })
        self.assertTrue(consent.is_active())
        self.assertEqual(consent.load()["source"], "env")

    def test_contributor_id_is_random_and_not_derived(self):
        first = consent.grant("community")["contributor_id"]
        consent.revoke()
        second = consent.grant("community")["contributor_id"]
        self.assertNotEqual(first, second)
        self.assertNotIn("gearbox", first.lower())

    def test_rotate_id_changes_pseudonym_and_leaves_receipt(self):
        consent.grant("community")
        old = consent.load()["contributor_id"]
        new = consent.rotate_id()
        self.assertNotEqual(old, new)
        receipts = consent.receipts_path().read_text(encoding="utf-8").strip().splitlines()
        self.assertTrue(any(json.loads(r)["kind"] == "rotated" for r in receipts))

    def test_disable_stops_sending_but_keeps_record(self):
        consent.grant("community")
        consent.disable()
        self.assertFalse(consent.is_active())
        self.assertEqual(consent.load()["status"], consent.STATUS_GRANTED)

    def test_revoke_invalidates_and_leaves_receipt(self):
        consent.grant("community")
        consent.revoke()
        record = consent.load()
        self.assertEqual(record["status"], consent.STATUS_REVOKED)
        self.assertIsNone(record["contributor_id"])
        self.assertFalse(consent.is_active())
        self.assertTrue(consent.receipts_path().exists())

    def test_self_hosted_requires_endpoint(self):
        with self.assertRaises(ValueError):
            consent.grant("self-hosted")

    def test_explain_lists_what_is_never_sent(self):
        text = consent.EXPLAIN.format(mode="local", status="none")
        for phrase in ("prompts", "rutas", "tokens", "identificadores de sesión"):
            self.assertIn(phrase, text)


class CapsuleTests(IsolatedHome):
    def _seed(self, count: int = 3, prompt: str = "Implementa el módulo"):
        core = load_core()
        ids = []
        for index in range(count):
            route = core.classify(f"{prompt} {index}")
            record = core.record_prediction(route, f"{prompt} {index}", f"s{index}",
                                            "/home/gabriel/privado")
            args = type("A", (), {"task_id": record["task_id"], "outcome": "accepted",
                                  "rating": None, "reason": None})()
            core.cmd_feedback(args)
            ids.append(record["task_id"])
        return core, ids

    def test_capsule_contains_only_allowlisted_fields(self):
        self._seed()
        built, _ = gb_capsule.build("community")
        self.assertEqual(privacy.validate_capsule(built), [])
        privacy.assert_safe(built)

    def test_capsule_has_no_task_ids_or_paths(self):
        _, ids = self._seed()
        built, task_ids = gb_capsule.build("community")
        blob = json.dumps(built)
        for task_id in ids:
            self.assertNotIn(task_id, blob)
        self.assertNotIn("gabriel", blob.lower())
        self.assertNotIn("privado", blob)
        self.assertEqual(len(task_ids), len(ids))   # se devuelven APARTE, no dentro

    def test_period_is_a_week_not_a_timestamp(self):
        self._seed(1)
        built, _ = gb_capsule.build("community")
        self.assertRegex(built["generated_period"], r"^\d{4}-W\d{2}$")

    def test_preview_matches_exactly_what_would_be_sent(self):
        self._seed(2)
        built, _ = gb_capsule.build("community")
        text = gb_capsule.preview(built)
        # El JSON impreso en la vista previa se puede volver a parsear y debe ser
        # idéntico al objeto que se comprime y encola.
        body = text.split("──\n", 1)[1].rsplit("\n\n", 1)[0]
        shown = json.loads(body[:body.rindex("}") + 1])
        self.assertEqual(shown, built)
        self.assertIn(privacy.sha256_hex(privacy.canonical_json(built)), text)

    def test_events_without_feedback_are_not_eligible(self):
        core = load_core()
        route = core.classify("Implementa algo")
        core.record_prediction(route, "Implementa algo", "s", "/tmp/x")
        built, _ = gb_capsule.build("community")
        self.assertEqual(built["aggregate"]["event_count"], 0)

    def test_marked_events_are_not_sent_twice(self):
        self._seed(2)
        built, ids = gb_capsule.build("community")
        gb_capsule.mark_sent(ids, built["capsule_id"])
        second, _ = gb_capsule.build("community")
        self.assertEqual(second["aggregate"]["event_count"], 0)

    def test_other_local_only_reason_never_leaves(self):
        core, ids = self._seed(1)
        args = type("A", (), {"task_id": ids[0], "outcome": None,
                              "rating": None, "reason": "other_local_only"})()
        core.cmd_feedback(args)
        gb_capsule.clear_marks()
        built, _ = gb_capsule.build("community")
        self.assertEqual(built["events"][0]["feedback_reason"], "none")


class OutboxTests(IsolatedHome):
    def test_enqueue_then_duplicate_is_idempotent(self):
        outbox.enqueue(sample_capsule(), "1.0")
        outbox.enqueue(sample_capsule(), "1.0")
        self.assertEqual(outbox.stats()["pending"], 1)

    def test_capsule_with_secret_never_reaches_the_queue(self):
        bad = sample_capsule()
        bad["client_version"] = FAKE_SECRETS["anthropic"]
        with self.assertRaises((privacy.PrivacyViolation, ValueError)):
            outbox.enqueue(bad, "1.0")
        self.assertEqual(outbox.stats()["pending"], 0)
        self.assertEqual(list(outbox.outbox_dir().glob("*.gz")), [])

    def test_stored_payload_is_valid_gzip_of_canonical_json(self):
        entry = outbox.enqueue(sample_capsule(), "1.0")
        raw = gzip.decompress(outbox.payload(entry))
        self.assertEqual(json.loads(raw), sample_capsule())
        self.assertEqual(privacy.sha256_hex(raw), entry["payload_sha256"])

    def test_failure_schedules_backoff_and_keeps_entry(self):
        outbox.enqueue(sample_capsule(), "1.0")
        capsule_id = sample_capsule()["capsule_id"]
        status = outbox.mark_failed(capsule_id, "network_error")
        self.assertEqual(status, outbox.STATUS_PENDING)
        entry = outbox.entries()[0]
        self.assertEqual(entry["attempts"], 1)
        self.assertEqual(entry["last_error_code"], "network_error")
        self.assertEqual(outbox.due(), [])   # ya no vence ahora mismo

    def test_backoff_grows_and_has_deterministic_jitter(self):
        first = outbox.backoff_seconds(1, "abc")
        second = outbox.backoff_seconds(2, "abc")
        self.assertGreater(second, first)
        self.assertEqual(outbox.backoff_seconds(1, "abc"), first)
        self.assertNotEqual(outbox.backoff_seconds(1, "otro-id"), first)

    def test_gives_up_after_max_attempts_without_losing_trace(self):
        outbox.enqueue(sample_capsule(), "1.0")
        capsule_id = sample_capsule()["capsule_id"]
        for _ in range(outbox.MAX_ATTEMPTS):
            status = outbox.mark_failed(capsule_id, "timeout")
        self.assertEqual(status, outbox.STATUS_FAILED)
        self.assertEqual(outbox.stats()["failed"], 1)

    def test_sent_entry_drops_its_payload_file(self):
        outbox.enqueue(sample_capsule(), "1.0")
        outbox.mark_sent(sample_capsule()["capsule_id"])
        self.assertEqual(outbox.stats()["sent"], 1)
        self.assertEqual(list(outbox.outbox_dir().glob("*.gz")), [])

    def test_expired_entries_are_purged(self):
        outbox.enqueue(sample_capsule(), "1.0")
        future = datetime.now(timezone.utc) + timedelta(days=outbox.RETENTION_DAYS + 1)
        self.assertEqual(outbox.purge_expired(now=future), 1)
        self.assertEqual(outbox.stats()["expired"], 1)

    def test_purge_all_empties_queue_and_files(self):
        outbox.enqueue(sample_capsule(), "1.0")
        self.assertEqual(outbox.purge_all(), 1)
        self.assertEqual(outbox.stats()["pending"], 0)
        self.assertEqual(list(outbox.outbox_dir().glob("*.gz")), [])

    def test_oversized_capsule_is_rejected(self):
        big = sample_capsule()
        big["events"] = [dict(big["events"][0]) for _ in range(20000)]
        big["aggregate"] = {"event_count": len(big["events"])}
        with self.assertRaises((outbox.PayloadTooLarge, ValueError)):
            outbox.enqueue(big, "1.0")

    def test_corrupt_payload_file_is_reported_not_swallowed(self):
        entry = outbox.enqueue(sample_capsule(), "1.0")
        path = outbox.Path(entry["compressed_path"])
        path.write_bytes(b"no soy gzip")
        with self.assertRaises(Exception):
            gzip.decompress(outbox.payload(entry))


if __name__ == "__main__":
    unittest.main()
