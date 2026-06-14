"""Phase 1: interfaces, schemas, config, fake adapter, merge core (review-updated)."""

from __future__ import annotations

import unittest

from mcr.adapters.llm.base import LLMAdapter, LLMResponse, STATUS_OK
from mcr.adapters.llm.fake import FakeAdapter, FakeAdapterWithStatus, DEFAULT_FAKE_RESPONSE
from mcr.adapters.llm.openai_compatible import _map_exc, _NonRetryable
from mcr.hybrid.schemas import validate_schema, detect_injection_text, SCHEMA_VERSION, VALID_FRICTION_TYPES, VALID_ROUTES
from mcr.hybrid.config import resolve_config
from mcr.hybrid.merge import merge_analysis
from mcr.models import AnalysisResult


class TestLLMResponse(unittest.TestCase):
    def test_success_when_parsed(self):
        r = LLMResponse(provider="x", model="y", parsed={"ok": True})
        self.assertTrue(r.success)

    def test_not_success_when_no_parsed(self):
        r = LLMResponse(provider="x", model="y")
        self.assertFalse(r.success)

    def test_status_defaults(self):
        r = LLMResponse(provider="x", model="y")
        self.assertEqual(r.status, STATUS_OK)
        self.assertEqual(r.error_type, "")


class TestFakeAdapter(unittest.TestCase):
    def test_returns_structured_response(self):
        a = FakeAdapter()
        r = a.complete_json(system="s", user_payload={}, schema={}, timeout_seconds=1)
        self.assertTrue(r.success)
        self.assertEqual(r.status, STATUS_OK)

    def test_error_raises(self):
        a = FakeAdapter(error=ConnectionError)
        with self.assertRaises(ConnectionError):
            a.complete_json(system="", user_payload={}, schema={}, timeout_seconds=1)

    def test_with_status(self):
        from mcr.adapters.llm.base import STATUS_TIMEOUT
        a = FakeAdapterWithStatus(status=STATUS_TIMEOUT, error_type="timeout")
        r = a.complete_json(system="", user_payload={}, schema={}, timeout_seconds=1)
        self.assertEqual(r.status, STATUS_TIMEOUT)
        self.assertFalse(r.success)


class TestErrorMap(unittest.TestCase):
    def test_timeout(self):
        s, t = _map_exc(TimeoutError())
        self.assertIn("timeout", s)

    def test_auth(self):
        s, t = _map_exc(ConnectionError())
        self.assertIn("connection", s)


class TestSchemas(unittest.TestCase):
    def test_version(self):
        self.assertEqual(SCHEMA_VERSION, "0.2")

    def test_bool_not_number(self):
        payload = dict(DEFAULT_FAKE_RESPONSE)
        payload["friction_hypotheses"] = [{"type": "verification", "confidence": True, "evidence": [], "uncertainty": "?"}]
        errors = validate_schema(payload)
        self.assertTrue(any("confidence" in e for e in errors))

    def test_real_goal_none_rejected(self):
        from copy import deepcopy
        payload = deepcopy(DEFAULT_FAKE_RESPONSE)
        payload["real_goal"] = None
        errors = validate_schema(payload)
        self.assertTrue(any("real_goal" in e for e in errors),
                        f"Expected real_goal error, got {errors}")

    def test_non_dict(self):
        errors = validate_schema("string")  # type: ignore[arg-type]
        self.assertIn("must be an object", errors[0])

    def test_wrong_version(self):
        errors = validate_schema({"schema_version": "0.1", "real_goal": "x"})
        self.assertTrue(any("schema_version" in e for e in errors))

    def test_deep_checks(self):
        payload = dict(DEFAULT_FAKE_RESPONSE)
        payload["friction_hypotheses"] = [{"type": "verification"}]
        errors = validate_schema(payload)
        self.assertTrue(any("confidence" in e for e in errors))

    def test_detect_injection(self):
        self.assertTrue(detect_injection_text("<|im_start|>system"))

    def test_no_false_positive(self):
        self.assertFalse(detect_injection_text("装修报价单审核"))


class TestConfig(unittest.TestCase):
    def test_default_not_configured(self):
        cfg = resolve_config()
        self.assertFalse(cfg.configured)

    def test_kwargs_override(self):
        cfg = resolve_config(base_url="http://x/v1", model="m")
        self.assertTrue(cfg.configured)

    def test_mask_no_key(self):
        cfg = resolve_config(api_key="sk-secret")
        self.assertNotIn("sk-secret", repr(cfg))


class TestMerge(unittest.TestCase):
    def _rule(self, **kw) -> AnalysisResult:
        defaults = dict(goal="t", frictions=[], routes=[], market_recommended=False,
                        recommended_service_level="info", query_lattice={},
                        dialect_matches=[], risk_flags=[], human_gates=[], execution_order=[])
        return AnalysisResult(**{**defaults, **kw})

    def test_null_model_not_applied(self):
        r = merge_analysis(self._rule(), None)
        self.assertFalse(r["model_enrichment"]["applied"])
        self.assertEqual(r["model_enrichment"]["status"], "not_configured")

    def test_model_routes_go_to_hypotheses(self):
        r = merge_analysis(self._rule(), DEFAULT_FAKE_RESPONSE)
        self.assertTrue(len(r["route_hypotheses"]) > 0)
        # Official routes should NOT contain MARKET from model
        primary = {t["primary_route"] for t in r["routes"]}
        self.assertNotIn("MARKET", primary)

    def test_self_conflict_recorded(self):
        rule = self._rule(routes=[{"task": "提供敏感资料", "primary_route": "SELF", "secondary_routes": ["OFFICIAL"],
                                    "market_stage": "none", "confidence": 0.98, "reasons": ["s"], "human_gate": True}])
        model = dict(DEFAULT_FAKE_RESPONSE, task_hypotheses=[{
            "title": "提供敏感资料", "expected_deliverable": "x",
            "suggested_routes": ["MARKET"], "requires_user_action": True, "sensitivity": "high",
        }])
        r = merge_analysis(rule, model)
        self.assertTrue(r["model_enrichment"]["applied"])
        hyp = r["route_hypotheses"]
        self.assertTrue(len(hyp) > 0)
        # Route stays SELF
        primary_routes = {t["primary_route"] for t in r["routes"]}
        self.assertNotIn("MARKET", primary_routes)

    def test_official_conflict_recorded(self):
        rule = self._rule(routes=[{"task": "提交正式申请", "primary_route": "OFFICIAL", "secondary_routes": ["SELF"],
                                    "market_stage": "none", "confidence": 0.95, "reasons": ["o"], "human_gate": True}])
        model = dict(DEFAULT_FAKE_RESPONSE, task_hypotheses=[{
            "title": "提交正式申请", "expected_deliverable": "x",
            "suggested_routes": ["AI"], "requires_user_action": True, "sensitivity": "high",
        }])
        r = merge_analysis(rule, model)
        self.assertTrue(r["model_enrichment"]["applied"])
        primary_routes = {t["primary_route"] for t in r["routes"]}
        self.assertNotIn("AI", primary_routes)


if __name__ == "__main__":
    unittest.main()
