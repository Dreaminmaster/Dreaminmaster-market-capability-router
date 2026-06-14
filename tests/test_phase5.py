"""Phase 5: CLI modes, hybrid, simple task guard (review-updated)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mcr.engine import MarketCapabilityRouter
from mcr.adapters.llm.fake import FakeAdapter, FakeAdapterWithStatus
from mcr.adapters.llm.base import STATUS_TIMEOUT, STATUS_OK
from mcr.hybrid.config import LLMConfig


class TestCLIModes(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run([sys.executable, "-m", "mcr.cli"] + list(args),
                              capture_output=True, text=True, timeout=30)

    def test_rules_with_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", encoding="utf-8", delete=False) as f:
            f.write("装修报价看不懂")
            tmp = f.name
        try:
            proc = self._run("analyze", f"@{tmp}", "--mode", "rules")
            self.assertEqual(proc.returncode, 0)
            self.assertIn("goal", json.loads(proc.stdout))
        finally:
            Path(tmp).unlink()

    def test_model_rejected(self):
        proc = self._run("analyze", "x", "--mode", "model")
        self.assertEqual(proc.returncode, 2)


class CountingAdapter(FakeAdapter):
    def __init__(self):
        super().__init__()
        self.call_count = 0

    def complete_json(self, **kw):
        self.call_count += 1
        return super().complete_json(**kw)


class TestHybrid(unittest.TestCase):
    def test_hybrid_ok(self):
        engine = MarketCapabilityRouter()
        adapter = CountingAdapter()
        config = LLMConfig(base_url="http://x", model="m")
        r = engine.analyze_with_model("装修报价看不懂", adapter=adapter, config=config)
        self.assertTrue(r["model_enrichment"]["applied"])
        self.assertEqual(r["model_enrichment"]["status"], STATUS_OK)
        self.assertEqual(adapter.call_count, 1)

    def test_no_config(self):
        engine = MarketCapabilityRouter()
        r = engine.analyze_with_model("hello", adapter=None, config=LLMConfig())
        self.assertFalse(r["model_enrichment"]["attempted"])

    def test_timeout_status(self):
        """Adapter returning timeout status propagates to model_enrichment."""
        engine = MarketCapabilityRouter()
        adapter = FakeAdapterWithStatus(status=STATUS_TIMEOUT, error_type="timeout")
        config = LLMConfig(base_url="http://x", model="m")
        r = engine.analyze_with_model("装修报价看不懂", adapter=adapter, config=config)
        self.assertEqual(r["model_enrichment"]["status"], STATUS_TIMEOUT)
        self.assertFalse(r["model_enrichment"]["applied"])

    def test_simple_task_no_call(self):
        """Simple writing with configured adapter → call_count == 0."""
        engine = MarketCapabilityRouter()
        adapter = CountingAdapter()
        config = LLMConfig(base_url="http://x", model="m")
        r = engine.analyze_with_model("把这句话改得更通顺", adapter=adapter, config=config)
        self.assertEqual(adapter.call_count, 0)
        self.assertFalse(r["model_enrichment"]["applied"])

    def test_rewrite_no_call(self):
        engine = MarketCapabilityRouter()
        adapter = CountingAdapter()
        config = LLMConfig(base_url="http://x", model="m")
        r = engine.analyze_with_model("润色一下这段文字", adapter=adapter, config=config)
        self.assertEqual(adapter.call_count, 0)

    def test_translation_with_qualification_calls(self):
        """翻译法律文件 → 有 qualification context → 应该触发"""
        engine = MarketCapabilityRouter()
        adapter = CountingAdapter()
        config = LLMConfig(base_url="http://x", model="m")
        r = engine.analyze_with_model("我需要找有资质的人翻译并公证法律文件",
                                      adapter=adapter, config=config)
        self.assertEqual(adapter.call_count, 1)

    def test_bare_translation_no_call(self):
        """纯翻译 → 不触发"""
        engine = MarketCapabilityRouter()
        adapter = CountingAdapter()
        config = LLMConfig(base_url="http://x", model="m")
        r = engine.analyze_with_model("帮我翻译一句话", adapter=adapter, config=config)
        self.assertEqual(adapter.call_count, 0)


if __name__ == "__main__":
    unittest.main()
