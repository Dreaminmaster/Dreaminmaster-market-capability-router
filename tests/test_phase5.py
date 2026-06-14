"""Phase 5 tests: CLI modes, hybrid with fake adapter, OpenMinis smoke, simple task guard."""

from __future__ import annotations

import json
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mcr.engine import MarketCapabilityRouter
from mcr.adapters.llm.fake import FakeAdapter
from mcr.hybrid.config import LLMConfig


class TestCLIModes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mcr_bin = (
            Path(__file__).resolve().parent.parent
            / ".venv" / "bin" / "mcr"
        )
        if not cls.mcr_bin.exists():
            cls.mcr_bin = Path(
                "/root/Dreaminmaster-market-capability-router"
                "/.venv/bin/mcr"
            )

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(self.mcr_bin)] + list(args),
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
            self.assertNotIn("model_enrichment", data)  # rules mode returns raw AnalysisResult
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


class TestHybridWithFake(unittest.TestCase):
    """Hybrid mode with FakeAdapter via programmatic API."""

    def test_hybrid_fake_enrichment_applied(self):
        engine = MarketCapabilityRouter()
        adapter = FakeAdapter()
        config = LLMConfig(base_url="http://fake", model="fake-model")

        result = engine.analyze_with_model(
            "装修报价单看不懂，想找人审核",
            adapter=adapter,
            config=config,
        )
        enrichment = result.get("model_enrichment", {})
        self.assertTrue(enrichment["applied"])
        self.assertEqual(enrichment["status"], "ok")

    def test_hybrid_no_config_returns_rules(self):
        engine = MarketCapabilityRouter()
        adapter = None
        config = LLMConfig()  # not configured

        result = engine.analyze_with_model(
            "装修报价单看不懂",
            adapter=adapter,
            config=config,
        )
        enrichment = result.get("model_enrichment", {})
        self.assertFalse(enrichment["applied"])
        self.assertEqual(enrichment["status"], "not_configured")


class TestSimpleTaskGuard(unittest.TestCase):
    """Simple writing tasks should not invoke model or market."""

    def test_simple_writing_not_market(self):
        engine = MarketCapabilityRouter()
        result = engine.analyze("把这句话改得更通顺")
        # Rules-only: no market recommended
        self.assertFalse(result.market_recommended)
        self.assertEqual(result.recommended_service_level, "information")

    def test_simple_writing_hybrid_no_enrichment(self):
        """Even in hybrid mode, simple tasks get rules-only (adapter None)."""
        engine = MarketCapabilityRouter()
        result = engine.analyze_with_model(
            "把这句话改得更通顺",
            adapter=None,
            config=LLMConfig(),
        )
        enrichment = result.get("model_enrichment", {})
        self.assertFalse(enrichment["applied"])
        # Market not recommended
        self.assertFalse(result.get("market_recommended", True))


if __name__ == "__main__":
    unittest.main()
