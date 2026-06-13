import tempfile
import unittest
from pathlib import Path

from mcr.outcome import OutcomeStore


class OutcomeTests(unittest.TestCase):
    def test_write_safe_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "outcomes.jsonl"
            OutcomeStore(path).append({"case_id":"x","chosen_route":"MARKET","success":True})
            self.assertTrue(path.exists())

    def test_reject_sensitive_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                OutcomeStore(Path(tmp)/"o.jsonl").append({"case_id":"x","password":"secret"})


if __name__ == "__main__":
    unittest.main()
