"""Review fixes: schema edge cases, redaction, per-task routing, engine status."""

from __future__ import annotations

import unittest

from mcr.engine import MarketCapabilityRouter
from mcr.hybrid.schemas import validate_schema
from mcr.hybrid.validation import redact_recursive
from mcr.hybrid.merge import merge_analysis
from mcr.adapters.llm.fake import DEFAULT_FAKE_RESPONSE, FakeAdapterWithStatus
from mcr.adapters.llm.base import (
    STATUS_TIMEOUT, STATUS_CONNECTION_ERROR, STATUS_AUTH_ERROR,
    STATUS_HTTP_ERROR, STATUS_INVALID_JSON, STATUS_OK,
)
from mcr.hybrid.config import LLMConfig
from mcr.models import AnalysisResult


class TestBoolNotNumber(unittest.TestCase):
    def test_confidence_true_rejected(self):
        payload = dict(DEFAULT_FAKE_RESPONSE)
        payload["friction_hypotheses"] = [{"type": "verification", "confidence": True, "evidence": [], "uncertainty": "?"}]
        errors = validate_schema(payload)
        self.assertTrue(any("confidence" in e for e in errors))

    def test_evidence_not_array(self):
        payload = dict(DEFAULT_FAKE_RESPONSE)
        payload["friction_hypotheses"] = [{"type": "verification", "confidence": 0.5, "evidence": "not array", "uncertainty": "?"}]
        errors = validate_schema(payload)
        self.assertTrue(any("evidence" in e for e in errors))

    def test_uncertainty_not_string(self):
        payload = dict(DEFAULT_FAKE_RESPONSE)
        payload["friction_hypotheses"] = [{"type": "verification", "confidence": 0.5, "evidence": [], "uncertainty": 42}]
        errors = validate_schema(payload)
        self.assertTrue(any("uncertainty" in e for e in errors))

    def test_deliverable_not_string(self):
        payload = dict(DEFAULT_FAKE_RESPONSE)
        payload["task_hypotheses"] = [{"title": "t", "expected_deliverable": 123, "suggested_routes": ["AI"],
                                       "requires_user_action": False, "sensitivity": "low"}]
        errors = validate_schema(payload)
        self.assertTrue(any("expected_deliverable" in e for e in errors))

    def test_dialect_term_not_string(self):
        payload = dict(DEFAULT_FAKE_RESPONSE)
        payload["unknown_dialect_hypotheses"] = [{"term": 123, "possible_meanings": ["x"], "confidence": 0.5, "evidence_required": []}]
        errors = validate_schema(payload)
        self.assertTrue(any("term" in e for e in errors))

    def test_oversized_string(self):
        payload = dict(DEFAULT_FAKE_RESPONSE)
        payload["real_goal"] = "x" * 600
        errors = validate_schema(payload)
        self.assertTrue(any("real_goal" in e for e in errors))

    def test_requires_user_action_not_bool(self):
        payload = dict(DEFAULT_FAKE_RESPONSE)
        payload["task_hypotheses"] = [{"title": "t", "expected_deliverable": "x", "suggested_routes": ["AI"],
                                       "requires_user_action": 1, "sensitivity": "low"}]
        errors = validate_schema(payload)
        self.assertTrue(any("requires_user_action" in e for e in errors))


class TestDedupRedaction(unittest.TestCase):
    def test_same_secret_twice(self):
        secret = "password=abc123"
        data = {"a": secret, "b": secret}
        result, warnings = redact_recursive(data)
        self.assertNotIn("abc123", result["a"])
        self.assertNotIn("abc123", result["b"])
        self.assertTrue(len(warnings) > 0)


class TestEngineStatuses(unittest.TestCase):
    """Engine must propagate structured adapter status to model_enrichment."""

    def _run(self, status, error_type=""):
        engine = MarketCapabilityRouter()
        adapter = FakeAdapterWithStatus(status=status, error_type=error_type)
        config = LLMConfig(base_url="http://x", model="m")
        return engine.analyze_with_model("装修报价看不懂", adapter=adapter, config=config)

    def test_timeout(self):
        r = self._run(STATUS_TIMEOUT, "timeout")
        self.assertEqual(r["model_enrichment"]["status"], STATUS_TIMEOUT)
        self.assertFalse(r["model_enrichment"]["applied"])

    def test_connection_error(self):
        r = self._run(STATUS_CONNECTION_ERROR, "connection_error")
        self.assertEqual(r["model_enrichment"]["status"], STATUS_CONNECTION_ERROR)

    def test_auth_error(self):
        r = self._run(STATUS_AUTH_ERROR, "auth_error")
        self.assertEqual(r["model_enrichment"]["status"], STATUS_AUTH_ERROR)

    def test_http_error(self):
        r = self._run(STATUS_HTTP_ERROR, "http_error")
        self.assertEqual(r["model_enrichment"]["status"], STATUS_HTTP_ERROR)

    def test_invalid_json(self):
        r = self._run(STATUS_INVALID_JSON, "invalid_json")
        self.assertEqual(r["model_enrichment"]["status"], STATUS_INVALID_JSON)


class TestPerTaskRouting(unittest.TestCase):
    def test_task_b_not_forced_official(self):
        rule = AnalysisResult(
            goal="t", frictions=[], routes=[
                {"task": "submit official", "primary_route": "OFFICIAL", "secondary_routes": ["SELF"],
                 "market_stage": "none", "confidence": 0.95, "reasons": ["o"], "human_gate": True},
            ],
            market_recommended=False, recommended_service_level="info",
            query_lattice={}, dialect_matches=[], risk_flags=[], human_gates=[], execution_order=[],
        )
        model = dict(DEFAULT_FAKE_RESPONSE, task_hypotheses=[{
            "title": "find review service", "expected_deliverable": "r",
            "suggested_routes": ["MARKET"], "requires_user_action": False, "sensitivity": "low",
        }])
        r = merge_analysis(rule, model)
        hyp = r["route_hypotheses"]
        review = [h for h in hyp if "review" in h.get("task", "")]
        self.assertTrue(len(review) > 0)
        self.assertIn("MARKET", review[0].get("suggested_routes", []))


if __name__ == "__main__":
    unittest.main()
