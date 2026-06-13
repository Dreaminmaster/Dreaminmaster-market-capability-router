import json
import unittest
from pathlib import Path

from mcr.candidate import CandidateEvaluator


class CandidateTests(unittest.TestCase):
    def test_safe_candidate(self):
        data = json.loads(Path("examples/candidates/renovation_review.json").read_text(encoding="utf-8"))
        result = CandidateEvaluator().evaluate(data, ["装修", "报价"])
        self.assertEqual(result.status, "worth_asking")
        self.assertLess(result.risk, 50)

    def test_risky_candidate(self):
        data = json.loads(Path("examples/candidates/account_service.json").read_text(encoding="utf-8"))
        result = CandidateEvaluator().evaluate(data, ["账号", "解封"])
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.risk, 100)


if __name__ == "__main__":
    unittest.main()
