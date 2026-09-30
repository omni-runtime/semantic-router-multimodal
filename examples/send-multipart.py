#!/usr/bin/env python3
"""Small explicit client for native multipart examples; performs one request."""
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
import uuid

fixture = Path(sys.argv[1]).resolve()
spec = json.loads(fixture.read_text())
boundary = "example-"+uuid.uuid4().hex
body = bytearray()
for name,value in spec["fields"].items():
    body.extend((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n').encode())
for file in spec["files"]:
    path = (fixture.parent/file["path"]).resolve()
    if not path.is_relative_to(fixture.parent):
        raise ValueError("example upload must stay inside its fixture directory")
    body.extend((f'--{boundary}\r\nContent-Disposition: form-data; name="{file["name"]}"; filename="{path.name}"\r\nContent-Type: {file["content_type"]}\r\n\r\n').encode())
    body.extend(path.read_bytes())
    body.extend(b"\r\n")
body.extend((f'--{boundary}--\r\n').encode())
request = urllib.request.Request(os.environ["GATEWAY_URL"].rstrip("/")+spec["path"],bytes(body),
    {"Authorization":"Bearer "+os.environ["GATEWAY_TOKEN"],"Content-Type":"multipart/form-data; boundary="+boundary},method="POST")
try:
    response = urllib.request.urlopen(request,timeout=120)
except urllib.error.HTTPError as error:
    response = error
with response:
    print(f"HTTP {response.status}; {response.headers.get('Content-Type','')}",file=sys.stderr)
    while chunk := response.read(65536):
        sys.stdout.buffer.write(chunk)
    raise SystemExit(0 if 200<=response.status<300 else 1)
