#!/usr/bin/env python3
"""Reassemble base64 zip parts into dist/ and verify sha256."""
from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "_staging" / "batch-01"
DEST = ROOT / "dist"
manifest = json.loads((SRC / "manifest.json").read_text())
DEST.mkdir(parents=True, exist_ok=True)
ok = True
for item in manifest:
    out = DEST / item["zip"]
    chunks = []
    for part in item["parts"]:
        text = (SRC / part["name"]).read_text().strip()
        chunks.append(base64.b64decode(text))
    data = b"".join(chunks)
    digest = hashlib.sha256(data).hexdigest()
    if digest != item["sha256"] or len(data) != item["size"]:
        print(f"MISMATCH {item['zip']}: got {len(data)} {digest}", file=sys.stderr)
        ok = False
        continue
    out.write_bytes(data)
    print(f"OK {item['zip']} {len(data)} {digest}")
if not ok:
    sys.exit(1)
