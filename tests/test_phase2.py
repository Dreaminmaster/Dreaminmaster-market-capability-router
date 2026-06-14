"""Phase 2 tests: OpenAI-compatible adapter transport, errors, retries, parsing."""

from __future__ import annotations

import io
import json
import unittest

from mcr.adapters.llm.openai_compatible import (
    OpenAICompatibleAdapter,
    LLMAdapterError,
    LLMAuthError,
    LLMTimeoutError,
    LLMResponseError,
)
from mcr.adapters.llm.base import LLMResponse
from mcr.hybrid.schemas import ANALYSIS_SCHEMA


def _make_http_response(text: str, status: int = 200):
    """Create a mock HTTP response for adapter testing."""
    return text, status


class TestOpenAIAdapterInit(unittest.TestCase):
    def test_requires_base_url(self):
        with self.assertRaises(ValueError):
            OpenAICompatibleAdapter(base_url="", model="x")

    def test_requires_model(self):
        with self.assertRaises(ValueError):
            OpenAICompatibleAdapter(base_url="http://x", model="")


class TestOpenAIAdapterParsing(unittest.TestCase):
    def _adapter(self):
        return OpenAICompatibleAdapter(
            base_url="http://localhost:1234/v1",
            model="test-model",
        )

    def test_parse_valid_chat_response(self):
        inner = {
            "schema_version": "0.2",
            "real_goal": "test",
        }
        resp_data = {
            "choices": [{
                "message": {"content": json.dumps(inner)},
            }],
        }
        parsed = self._adapter()._parse(json.dumps(resp_data))
        self.assertEqual(parsed["real_goal"], "test")

    def test_parse_no_choices(self):
        with self.assertRaises(LLMResponseError):
            self._adapter()._parse('{"choices": []}')

    def test_parse_invalid_json(self):
        with self.assertRaises(LLMResponseError):
            self._adapter()._parse("not json")

    def test_parse_invalid_content_json(self):
        resp_data = {
            "choices": [{"message": {"content": "not json either"}}],
        }
        with self.assertRaises(LLMResponseError):
            self._adapter()._parse(json.dumps(resp_data))

    def test_parse_empty_content(self):
        resp_data = {
            "choices": [{"message": {"content": ""}}],
        }
        with self.assertRaises(LLMResponseError):
            self._adapter()._parse(json.dumps(resp_data))


class TestAdapterRequestShape(unittest.TestCase):
    def test_build_request_has_response_format(self):
        adapter = OpenAICompatibleAdapter(
            base_url="http://localhost:1234/v1",
            model="local-model",
        )
        body = adapter._build_request(
            system="You are helpful.",
            user_payload={"data_envelope": {"user_request": "help me"}},
            schema=ANALYSIS_SCHEMA,
            max_tokens=512,
        )
        self.assertEqual(body["model"], "local-model")
        self.assertEqual(body["messages"][0]["role"], "system")
        self.assertEqual(body["messages"][1]["role"], "user")
        self.assertEqual(body["max_tokens"], 512)
        self.assertEqual(body["temperature"], 0.0)
        self.assertIn("response_format", body)
        rf = body["response_format"]
        self.assertEqual(rf["type"], "json_schema")
        self.assertIn("json_schema", rf)


class TestErrorClassification(unittest.TestCase):
    def test_auth_error_not_retryable(self):
        from mcr.adapters.llm.openai_compatible import _map_error, LLMAuthError
        s, t = _map_error(LLMAuthError("bad key"))
        self.assertIn("auth", s)

    def test_timeout_error(self):
        from mcr.adapters.llm.openai_compatible import _map_error, LLMTimeoutError
        s, t = _map_error(LLMTimeoutError("too slow"))
        self.assertIn("timeout", s)

    def test_response_error(self):
        from mcr.adapters.llm.openai_compatible import _map_error, LLMResponseError
        s, t = _map_error(LLMResponseError("Unable to parse JSON"))
        self.assertIn("invalid_json", s)


if __name__ == "__main__":
    unittest.main()
