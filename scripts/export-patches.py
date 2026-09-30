#!/usr/bin/env python3
"""Export the isolated development diff as the ordered authoritative patch set."""
import hashlib
import json
from pathlib import Path
import subprocess
import argparse

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--checkout", type=Path, default=root / ".work/upstream")
checkout = parser.parse_args().checkout.resolve()
lock = json.loads((root / "upstream.lock.json").read_text())
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
if head != lock["commit"]:
    raise SystemExit("development checkout differs from upstream lock")
# Intent-to-add makes new source/test files part of the diff without committing.
paths = ["src/semantic-router", "src/vllm-sr/cli", "candle-binding", "dashboard/frontend/src/generated",
         "config/config.yaml", "config/catalog", "config/recipes/built-in/latest/catalog.yaml",
         "tools/catalog", "website/static/model-catalog", "website/static/openapi", "website/docs/api"]
subprocess.run(["git", "add", "--intent-to-add", *paths], cwd=checkout, check=True)
patch = subprocess.check_output(["git", "diff", "--binary", "HEAD", "--", *paths], cwd=checkout)
if not patch:
    raise SystemExit("no changes to export")
name = "0001-native-multimodal.patch"
(root / "patches" / name).write_bytes(patch)
(root / "patches/series").write_text(name + "\n")
(root / "patches/checksums.json").write_text(json.dumps({name: hashlib.sha256(patch).hexdigest()}, indent=2) + "\n")
print(f"Exported {len(patch)} bytes; run prepare + test in a fresh checkout.")
