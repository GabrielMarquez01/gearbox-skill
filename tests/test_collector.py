"""Colector de referencia y priors comunitarios.

Pruebas negativas primero: lo que el colector debe RECHAZAR importa más que lo
que acepta.
"""
from __future__ import annotations

import gzip
import hashlib
import hmac
import json
import os
import time
import unittest
from unittest import mock
from hashlib import sha256

import sys as _sys
from pathlib import Path as _Path
# Permite invocar tanto `unittest discover -s tests` como
# `unittest tests.test_x`: en el segundo caso este directorio no queda
# en sys.path y `support` no se encontraría.
_sys.path.insert(0, str(_Path(__file__).resolve().parent))

from support import FAKE_SECRETS, IsolatedHome, sample_capsule

from collector import aggregation, schema, security
from collector.app import Collector
from collector.storage import Storage
from gearboxlib import priors


def gz(payload: dict) -> tuple[bytes, str]:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return gzip.compress(raw), sha256(raw).hexdigest()


def headers(digest: str, capsule_id: str, contributor: str = "contrib-1") -> dict[str, str]:
    return {
        "content-encoding": "gzip",
        "x-gearbox-content-sha256": digest,
        "idempotency-key": capsule_id,
        "x-gearbox-contributor": contributor,
    }


def current_period() -> str:
    now = time.gmtime()
    return f"{now.tm_year}-W{int(time.strftime('%V', now)):02d}"


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.collector = Collector(Storage())

    def post(self, capsule: dict, extra: dict | None = None, contributor: str = "c1"):
        body, digest = gz(capsule)
        head = headers(digest, str(capsule["capsule_id"]), contributor)
        head.update(extra or {})
        status, _, payload = self.collector.handle("POST", "/v1/capsules", head, body)
        return status, json.loads(payload)

    def test_accepts_a_valid_capsule(self):
        status, body = self.post(sample_capsule(generated_period=current_period()))
        self.assertEqual(status, 202)
        self.assertEqual(body["status"], "accepted")

    def test_rejects_unknown_top_level_field(self):
        capsule = sample_capsule(generated_period=current_period())
        capsule["prompt"] = "texto del usuario"
        status, body = self.post(capsule)
        self.assertEqual(status, 422)
        self.assertEqual(body["error"], "schema_invalid")

    def test_rejects_free_text_in_event(self):
        capsule = sample_capsule(generated_period=current_period())
        capsule["events"][0]["feedback_reason"] = "porque el resultado no me sirvió para nada"
        status, body = self.post(capsule)
        self.assertEqual(status, 422)

    def test_rejects_value_outside_enum(self):
        capsule = sample_capsule(generated_period=current_period())
        capsule["events"][0]["predicted_gear"] = "G9"
        self.assertEqual(self.post(capsule)[0], 422)

    def test_rejects_non_gzip_body(self):
        capsule = sample_capsule(generated_period=current_period())
        raw = json.dumps(capsule).encode()
        status, _, payload = self.collector.handle(
            "POST", "/v1/capsules",
            {"x-gearbox-content-sha256": sha256(raw).hexdigest()}, raw)
        self.assertEqual(status, 415)
        self.assertEqual(json.loads(payload)["error"], "gzip_required")

    def test_rejects_zip_bomb(self):
        bomb = gzip.compress(b"A" * (security.MAX_DECOMPRESSED_BYTES + 1024))
        status, _, payload = self.collector.handle(
            "POST", "/v1/capsules",
            {"content-encoding": "gzip"}, bomb)
        self.assertEqual(status, 413)
        self.assertEqual(json.loads(payload)["error"], "decompression_bomb")

    def test_rejects_oversized_body(self):
        body = b"x" * (security.MAX_BODY_BYTES + 1)
        status, _, payload = self.collector.handle(
            "POST", "/v1/capsules", {"content-encoding": "gzip"}, body)
        self.assertEqual(status, 413)

    def test_rejects_content_hash_mismatch(self):
        capsule = sample_capsule(generated_period=current_period())
        body, _ = gz(capsule)
        head = headers("0" * 64, str(capsule["capsule_id"]))
        status, _, payload = self.collector.handle("POST", "/v1/capsules", head, body)
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(payload)["error"], "content_hash_mismatch")

    def test_rejects_idempotency_key_mismatch(self):
        capsule = sample_capsule(generated_period=current_period())
        status, body = self.post(capsule, extra={"idempotency-key": "otra-cosa"})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "idempotency_mismatch")

    def test_replay_of_same_capsule_is_deduplicated(self):
        capsule = sample_capsule(generated_period=current_period())
        self.assertEqual(self.post(capsule)[0], 202)
        status, body = self.post(capsule)
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "duplicate")

    def test_rejects_stale_period(self):
        status, body = self.post(sample_capsule(generated_period="2019-W02"))
        self.assertEqual(status, 422)
        self.assertEqual(body["error"], "period_too_old")

    def test_rate_limit_kicks_in(self):
        limiter = security.RateLimiter(limit=3)
        collector = Collector(Storage(), rate_limiter=limiter)
        last = 0
        for index in range(5):
            capsule = sample_capsule(
                capsule_id=f"1111111{index}-2222-4333-8444-555555555555",
                generated_period=current_period())
            body, digest = gz(capsule)
            last, _, payload = collector.handle(
                "POST", "/v1/capsules", headers(digest, capsule["capsule_id"]), body)
        self.assertEqual(last, 429)
        self.assertEqual(json.loads(payload)["error"], "rate_limited")

    def test_auth_required_when_token_configured(self):
        collector = Collector(Storage(), token="s3cret-token")
        capsule = sample_capsule(generated_period=current_period())
        body, digest = gz(capsule)
        status, _, _ = collector.handle("POST", "/v1/capsules",
                                        headers(digest, capsule["capsule_id"]), body)
        self.assertEqual(status, 401)
        head = headers(digest, capsule["capsule_id"])
        head["authorization"] = "Bearer s3cret-token"
        self.assertEqual(collector.handle("POST", "/v1/capsules", head, body)[0], 202)

    def test_error_response_never_echoes_token(self):
        collector = Collector(Storage(), token="s3cret-token")
        head = {"content-encoding": "gzip", "authorization": "Bearer s3cret-token"}
        _, _, payload = collector.handle("POST", "/v1/capsules", head, b"basura")
        self.assertNotIn("s3cret-token", payload.decode())

    def test_deletion_request_removes_raw_capsules(self):
        capsule = sample_capsule(generated_period=current_period())
        self.post(capsule, contributor="borrame")
        status, _, payload = self.collector.handle(
            "POST", "/v1/deletion-requests", {},
            json.dumps({"contributor_id": "borrame"}).encode())
        self.assertEqual(status, 202)
        self.assertEqual(json.loads(payload)["raw_capsules_deleted"], 1)

    def test_health_exposes_no_pii(self):
        self.post(sample_capsule(generated_period=current_period()), contributor="quien-sea")
        _, _, payload = self.collector.handle("GET", "/health", {})
        text = payload.decode()
        self.assertNotIn("quien-sea", text)
        self.assertIn("retention_days", text)


class RetentionAndAggregationTests(unittest.TestCase):
    def setUp(self):
        self.storage = Storage()
        self.collector = Collector(self.storage)

    def _ingest(self, count: int, contributors: int = 6, outcome: str = "accepted"):
        for index in range(count):
            event = dict(sample_capsule()["events"][0])
            event["outcome"] = outcome
            capsule = sample_capsule(
                capsule_id=f"{index:08d}-2222-4333-8444-555555555555",
                generated_period=current_period(),
                events=[event], aggregate={"event_count": 1})
            body, digest = gz(capsule)
            self.collector.handle(
                "POST", "/v1/capsules",
                headers(digest, capsule["capsule_id"], f"contrib-{index % contributors}"), body)

    def test_raw_is_deleted_after_aggregation(self):
        self._ingest(3)
        aggregation.aggregate_pending(self.storage)
        self.assertEqual(self.storage.pending_raw(), [])
        rows = self.storage.conn.execute("SELECT COUNT(*) AS n FROM raw_capsules").fetchone()
        self.assertEqual(rows["n"], 0)
        self.assertTrue(self.storage.aggregates())

    def test_small_cohort_is_never_published(self):
        self._ingest(5)
        document = self.collector.priors()
        self.assertEqual(document["routes"], [])

    def test_cohort_above_threshold_is_published_as_bands(self):
        self._ingest(30)
        document = self.collector.priors()
        self.assertEqual(len(document["routes"]), 1)
        route = document["routes"][0]
        self.assertRegex(route["sample_band"], r"^\d+-\d+$|^\d+\+$")
        self.assertRegex(route["accepted_rate_band"], r"^\d\.\d-\d\.\d$")
        for value in route.values():
            self.assertNotRegex(str(value), r"^\d+$")   # ninguna cifra exacta

    def test_many_events_but_few_contributors_is_suppressed(self):
        self._ingest(30, contributors=2)
        self.assertEqual(self.collector.priors()["routes"], [])

    def test_expired_raw_is_purged(self):
        self._ingest(1)
        old = time.time() - 999 * 86400
        self.storage.conn.execute("UPDATE raw_capsules SET received_at=?", (old,))
        self.assertEqual(self.storage.purge_expired_raw(), 1)

    def test_individual_capsule_is_never_exposed(self):
        self._ingest(30)
        document = self.collector.priors()
        blob = json.dumps(document)
        self.assertNotIn("capsule_id", blob)
        self.assertNotIn("contrib-", blob)


class PriorsClientTests(IsolatedHome):
    def test_signature_is_revalidated_on_every_load(self):
        key = b"community-signing-key"
        document = self._document()
        document["signature"] = {
            "alg": "HMAC-SHA256",
            "value": hmac.new(
                key, priors.content_digest(document).encode(), hashlib.sha256
            ).hexdigest(),
        }
        with mock.patch.dict(os.environ, {"GEARBOX_PRIORS_HMAC_KEY": key.decode()}):
            priors.store(document, hmac_key=key)
            self.assertIsNotNone(priors.load())
            stored = json.loads(priors.priors_path().read_text())
            stored["routes"][0]["accepted_rate_band"] = "0.1-0.2"
            stored["content_sha256"] = priors.content_digest(stored)
            priors.priors_path().write_text(json.dumps(stored))
            self.assertIsNone(priors.load())

    def _document(self, samples: str = "25-49") -> dict:
        document = {
            "schema_version": "1.0",
            "generated_at": "2026-07-25",
            "minimum_cohort": 20,
            "routes": [{
                "task_type": "implementation", "gear": "G2", "model_family": "sonnet",
                "effort": "high", "sample_band": samples,
                "accepted_rate_band": "0.8-0.9", "rework_rate_band": "0.1-0.2",
            }],
        }
        document["content_sha256"] = priors.content_digest(document)
        return document

    def test_valid_document_is_accepted(self):
        self.assertEqual(priors.validate(self._document()), [])
        priors.store(self._document())
        self.assertEqual(priors.summary()["routes"], 1)

    def test_tampered_document_is_rejected(self):
        document = self._document()
        document["routes"][0]["accepted_rate_band"] = "0.9-1.0"
        with self.assertRaises(priors.PriorsRejected):
            priors.store(document)

    def test_missing_hash_is_rejected(self):
        document = self._document()
        document.pop("content_sha256")
        self.assertTrue(priors.validate(document))

    def test_incompatible_schema_is_rejected(self):
        document = self._document()
        document["schema_version"] = "2.0"
        document["content_sha256"] = priors.content_digest(document)
        self.assertTrue(priors.validate(document))

    def test_cohort_violation_is_rejected(self):
        document = self._document(samples="0-9")
        document["content_sha256"] = priors.content_digest(document)
        errors = priors.validate(document)
        self.assertTrue(any("cohorte" in e for e in errors))

    def test_last_valid_document_survives_a_rejection(self):
        priors.store(self._document())
        bad = self._document()
        bad["routes"][0]["gear"] = "G9"
        bad["content_sha256"] = priors.content_digest(bad)
        with self.assertRaises(priors.PriorsRejected):
            priors.store(bad)
        self.assertEqual(priors.summary()["routes"], 1)   # el bueno sigue ahí

    def test_hmac_signature_is_verified_when_key_present(self):
        import hmac as _hmac

        key = b"clave-de-prueba"
        document = self._document()
        document["signature"] = {
            "alg": "HMAC-SHA256",
            "value": _hmac.new(key, document["content_sha256"].encode(), sha256).hexdigest(),
        }
        self.assertEqual(priors.validate(document, hmac_key=key), [])
        document["signature"]["value"] = "0" * 64
        self.assertTrue(priors.validate(document, hmac_key=key))

    def test_priors_shift_prediction_but_never_the_human_gate(self):
        from support import load_core

        core = load_core()
        before = core.classify("Audita vulnerabilidades OAuth y datos personales")
        priors.store(self._document())
        after = core.classify("Audita vulnerabilidades OAuth y datos personales")
        self.assertTrue(before.human_gate)
        self.assertTrue(after.human_gate, "un prior comunitario jamás puede quitar el gate")
        self.assertEqual(before.gear, after.gear)

    def test_blended_prior_gives_way_to_local_evidence(self):
        far = priors.blended_prior(0.5, 0.9, local_samples=0)
        near = priors.blended_prior(0.5, 0.9, local_samples=200)
        self.assertGreater(far, near)
        self.assertAlmostEqual(near, 0.5, places=1)

    def test_corrupt_file_on_disk_is_ignored(self):
        priors.store(self._document())
        priors.priors_path().write_text('{"schema_version": "1.0"}', encoding="utf-8")
        self.assertIsNone(priors.load())


class SchemaNormalizationTests(unittest.TestCase):
    def test_client_version_is_normalized(self):
        self.assertEqual(schema.normalize_version("3.0.0-preview.2"), "3.0")
        self.assertEqual(schema.normalize_version("basura"), "unknown")

    def test_published_schema_declares_forbidden_fields(self):
        published = schema.published_schema()
        self.assertIn("prompt", published["x-forbidden-fields"])
        self.assertIn("session_id", published["x-forbidden-fields"])


if __name__ == "__main__":
    unittest.main()
