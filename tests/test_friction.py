import unittest

from mcr.friction import FrictionDiagnoser


class FrictionTests(unittest.TestCase):
    def test_verification(self):
        results = FrictionDiagnoser().diagnose("我担心装修报价单有问题，想审核")
        self.assertIn("verification", {r.friction_type for r in results})

    def test_diagnosis(self):
        results = FrictionDiagnoser().diagnose("账号申诉失败，不知道原因")
        self.assertIn("diagnosis", {r.friction_type for r in results})


if __name__ == "__main__":
    unittest.main()
