#!/usr/bin/env python3
"""Reassemble base64 zip parts into dist/ and verify sha256.
Items with a "retitle" key are built instead by downloading the already-published source asset, checking its sha256,
and rewriting only the TITLE line of listing.txt (scripts/retitle_core.py); all other zip members stay byte-identical.
Usage: reassemble_release.py [TAG]   (TAG defaults to env TAG, then batch-01; reads _staging/TAG/manifest.json)"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

TAG = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TAG", "batch-01")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SRC = ROOT / "_staging" / TAG
DEST = ROOT / "dist"
manifest = json.loads((SRC / "manifest.json").read_text())
DEST.mkdir(parents=True, exist_ok=True)


def fetch(url: str) -> bytes:
    last = None
    for _ in range(8):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except Exception as e:  # CDN can 404 intermittently
            last = e
            time.sleep(3)
    raise RuntimeError(f"download failed {url}: {last}")


ok = True
for item in manifest:
    out = DEST / item["zip"]
    if "retitle" in item:
        from retitle_core import retitle
        rt = item["retitle"]
        src = fetch(rt["source_url"])
        if hashlib.sha256(src).hexdigest() != rt["source_sha256"] or len(src) != rt["source_size"]:
            print(f"SOURCE MISMATCH {item['zip']}", file=sys.stderr)
            ok = False
            continue
        data = retitle(src, rt["new_title"], rt["old_title"])
    else:
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
