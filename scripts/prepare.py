#!/usr/bin/env python3
"""Prepare a new isolated checkout; never reset a developer's working tree."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="existing upstream clone, otherwise use locked repository")
    parser.add_argument("--output", type=Path, default=ROOT / ".work/prepared")
    args = parser.parse_args()
    lock = json.loads((ROOT / "upstream.lock.json").read_text())
    if args.output.exists():
        parser.error("output already exists; choose a new directory (no destructive reset)")
    series = ROOT / "patches/series"
    manifest = json.loads((ROOT / "patches/checksums.json").read_text())
    patches = [name for name in series.read_text().splitlines() if name and not name.startswith("#")]
    if set(patches) != set(manifest):
        parser.error("patch checksum manifest differs from series")
    for name in patches:
        if Path(name).name != name:
            parser.error("patch names must be plain basenames")
        if hashlib.sha256((ROOT / "patches" / name).read_bytes()).hexdigest() != manifest[name]:
            parser.error(f"patch checksum mismatch: {name}")
    run("git", "clone", "--no-hardlinks", "--no-checkout", args.source or lock["repository"], str(args.output))
    run("git", "checkout", "--detach", lock["commit"], cwd=args.output)
    for name in patches:
        patch = str(ROOT / "patches" / name)
        run("git", "apply", "--check", patch, cwd=args.output)
        run("git", "apply", patch, cwd=args.output)
    print(json.dumps({"checkout": str(args.output.resolve()), "upstream": lock["commit"], "patches": manifest}))


if __name__ == "__main__":
    main()
