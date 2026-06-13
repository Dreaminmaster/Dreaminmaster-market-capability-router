import unittest

from mcr.engine import MarketCapabilityRouter


class RoutingTests(unittest.TestCase):
    def test_account_official_and_self(self):
        result = MarketCapabilityRouter().analyze("账号申诉失败，对方还要验证码")
        routes = {r.primary_route for r in result.routes}
        self.assertIn("OFFICIAL", routes)
        self.assertIn("SELF", routes)
        self.assertTrue(any(f.severity == "critical" for f in result.risk_flags))
        self.assertFalse(result.market_recommended)

    def test_renovation_market_review(self):
        result = MarketCapabilityRouter().analyze("装修报价单看不懂，担心增项，想找人审核")
        self.assertTrue(result.market_recommended)
        self.assertEqual(result.recommended_service_level, "review")

    def test_simple_writing_not_market(self):
        result = MarketCapabilityRouter().analyze("请帮我把下面的文字整理得更清楚")
        self.assertFalse(result.market_recommended)


if __name__ == "__main__":
    unittest.main()
