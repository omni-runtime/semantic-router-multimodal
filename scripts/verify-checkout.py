#!/usr/bin/env python3
"""Verify build sources equal locked upstream plus the authoritative patch set.

Uses a temporary Git index; never edits the checkout, its real index or HEAD.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def verify(checkout):
    lock = json.loads((ROOT/'upstream.lock.json').read_text())
    checksums = json.loads((ROOT/'patches/checksums.json').read_text())
    names = [s for s in (ROOT/'patches/series').read_text().splitlines() if s and not s.startswith('#')]
    if set(names) != set(checksums): raise ValueError('patch series and checksum inventory differ')
    for name in names:
        if Path(name).name != name: raise ValueError('patch must be a plain basename')
        if hashlib.sha256((ROOT/'patches'/name).read_bytes()).hexdigest() != checksums[name]:
            raise ValueError('authoritative patch checksum mismatch: '+name)
    with tempfile.TemporaryDirectory(prefix='sr-verify-index-') as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory)/'index'))
        def git(*args):
            return subprocess.check_output(['git','-c','core.filemode=true','-c',f'safe.directory={checkout.resolve()}',*args], cwd=checkout, env=env, text=True).strip()
        if git('rev-parse','HEAD') != lock['commit']:
            raise ValueError('checkout HEAD differs from locked upstream')
        git('read-tree', lock['commit'])
        for name in names:
            git('apply','--cached',str(ROOT/'patches'/name))
        tree = git('write-tree')
        changed = git('diff','--name-only',tree,'--')
        unknown = git('ls-files','--others','--exclude-standard')
        if changed or unknown:
            raise ValueError('checkout differs from authoritative source tree: '+', '.join(filter(None,(changed,unknown))).replace('\n',', '))
    return {'upstream_commit':lock['commit'], 'prepared_tree':tree, 'patches':checksums,
            'source_verification':'worktree-equals-upstream-plus-patches'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    args = parser.parse_args()
    try: result = verify(args.checkout.resolve())
    except (ValueError, subprocess.CalledProcessError) as error: parser.exit(2, str(error)+'\n')
    print(json.dumps(result, sort_keys=True))
