import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

from mcr.api import MCRRequestHandler


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MCRRequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_health(self):
        with urlopen(self.base + "/health", timeout=3) as response:
            data = json.loads(response.read())
        self.assertEqual(data["status"], "ok")

    def test_analyze(self):
        body = json.dumps({"text": "装修报价单看不懂，担心增项"}, ensure_ascii=False).encode()
        req = Request(self.base + "/analyze", data=body, headers={"Content-Type":"application/json"}, method="POST")
        with urlopen(req, timeout=3) as response:
            data = json.loads(response.read())
        self.assertTrue(data["market_recommended"])


if __name__ == "__main__":
    unittest.main()
