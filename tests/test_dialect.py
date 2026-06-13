import unittest

from mcr.dialect import PlatformDialectEngine


class DialectTests(unittest.TestCase):
    def test_known_term(self):
        matches = PlatformDialectEngine().interpret("卖家说这是报价体检，拍前联系")
        concepts = {m["canonical_concept"] for m in matches}
        self.assertIn("装修报价审核", concepts)

    def test_unknown_term(self):
        matches = PlatformDialectEngine().interpret("完全未知的随机表达")
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
