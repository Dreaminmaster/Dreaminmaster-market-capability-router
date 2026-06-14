"""Phase 5 tests: CLI modes, hybrid with fake adapter, simple task guard."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mcr.engine import MarketCapabilityRouter
from mcr.adapters.llm.fake import FakeAdapter
from mcr.hybrid.config import LLMConfig


class TestCLIModes(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "mcr.cli"] + list(args),
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_rules_mode_with_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("装修报价单看不懂，想找人审核")
            tmp = f.name
        try:
            proc = self._run("analyze", f"@{tmp}", "--mode", "rules")
            self.assertEqual(proc.returncode, 0)
            data = json.loads(proc.stdout)
            self.assertIn("goal", data)
        finally:
            Path(tmp).unlink()

    def test_rules_mode_inline(self):
        proc = self._run("analyze", "装修报价单看不懂", "--mode", "rules")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIn("frictions", data)

    def test_model_mode_rejected(self):
        proc = self._run("analyze", "test", "--mode", "model")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("not supported", proc.stderr)

    def test_unknown_mode(self):
        proc = self._run("analyze", "test", "--mode", "quantum")
        self.assertEqual(proc.returncode, 2)


class CountingFakeAdapter(FakeAdapter):
    """FakeAdapter that counts calls for testing simple-task guard."""

    def __init__(self):
        super().__init__()
        self.call_count = 0

    def complete_json(self, **kwargs):
        self.call_count += 1
        return super().complete_json(**kwargs)


class TestHybridWithFake(unittest.TestCase):
    def test_hybrid_fake_enrichment_applied(self):
        engine = MarketCapabilityRouter()
        adapter = CountingFakeAdapter()
        config = LLMConfig(base_url="http://fake", model="fake-model")

        result = engine.analyze_with_model(
            "装修报价单看不懂，想找人审核",
            adapter=adapter,
            config=config,
        )
        enrichment = result.get("model_enrichment", {})
        self.assertTrue(enrichment["applied"])
        self.assertEqual(enrichment["status"], "ok")
        self.assertEqual(adapter.call_count, 1)

    def test_hybrid_no_config_returns_rules(self):
        engine = MarketCapabilityRouter()
        config = LLMConfig()

        result = engine.analyze_with_model(
            "装修报价单看不懂",
            adapter=None,
            config=config,
        )
        enrichment = result.get("model_enrichment", {})
        self.assertFalse(enrichment["attempted"])
        self.assertEqual(enrichment["status"], "not_configured")

    def test_hybrid_attempted_when_configured_even_on_failure(self):
        """attempted=true when adapter exists and config is set, even if call fails."""
        engine = MarketCapabilityRouter()
        adapter = FakeAdapter(error=ConnectionError)
        config = LLMConfig(base_url="http://fake", model="fake-model")

        result = engine.analyze_with_model(
            "装修报价单看不懂",
            adapter=adapter,
            config=config,
        )
        enrichment = result.get("model_enrichment", {})
        self.assertTrue(enrichment["attempted"])
        self.assertIn(enrichment["status"], ("connection_error",))


class TestSimpleTaskGuard(unittest.TestCase):
    def test_simple_writing_not_market(self):
        engine = MarketCapabilityRouter()
        result = engine.analyze("把这句话改得更通顺")
        self.assertFalse(result.market_recommended)
        self.assertEqual(result.recommended_service_level, "information")

    def test_simple_writing_not_calling_adapter(self):
        """With configured CountingFakeAdapter, simple task must not call it."""
        engine = MarketCapabilityRouter()
        adapter = CountingFakeAdapter()
        config = LLMConfig(base_url="http://fake", model="fake-model")

        result = engine.analyze_with_model(
            "把这句话改得更通顺",
            adapter=adapter,
            config=config,
        )
        self.assertEqual(adapter.call_count, 0,
                         "Simple writing task must not invoke model adapter")
        enrichment = result.get("model_enrichment", {})
        self.assertFalse(enrichment.get("applied", True))


if __name__ == "__main__":
    unittest.main()
