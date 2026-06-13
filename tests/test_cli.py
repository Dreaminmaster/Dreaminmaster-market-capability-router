import io
import tempfile
import unittest
from pathlib import Path

from mcr.cli import _load_candidate, _load_text


class CLITests(unittest.TestCase):
    def test_load_candidate_from_stdin(self):
        candidate = _load_candidate("-", io.StringIO('{"title":"装修报价审核"}'))
        self.assertEqual(candidate["title"], "装修报价审核")

    def test_load_candidate_rejects_array(self):
        with self.assertRaises(ValueError):
            _load_candidate("-", io.StringIO('[]'))

    def test_load_text_from_stdin(self):
        self.assertEqual(_load_text("-", io.StringIO("装修报价审核")), "装修报价审核")

    def test_load_text_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "request.txt"
            path.write_text("账号申诉失败", encoding="utf-8")
            self.assertEqual(_load_text(f"@{path}"), "账号申诉失败")


if __name__ == "__main__":
    unittest.main()
