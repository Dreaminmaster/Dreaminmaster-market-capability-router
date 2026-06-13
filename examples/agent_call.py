#!/usr/bin/env python3
import json
from urllib.request import Request, urlopen

payload = json.dumps({"text": "装修报价单看不懂，担心增项，想找人审核"}, ensure_ascii=False).encode("utf-8")
request = Request(
    "http://127.0.0.1:8765/analyze",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urlopen(request, timeout=10) as response:
    print(response.read().decode("utf-8"))
