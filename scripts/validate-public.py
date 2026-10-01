#!/usr/bin/env python3
"""Check public source structure, Markdown links, release evidence and patch hashes."""
import compileall
import hashlib
import json
from pathlib import Path
import re
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '.venv', '.work', '.state', 'dist', 'generated', 'reports', '__pycache__'}

def public_files():
    return [p for p in ROOT.rglob('*') if p.is_file() and not EXCLUDED.intersection(p.relative_to(ROOT).parts)]

def main():
    required = ['README.md', 'README.zh-CN.md', 'LICENSE', 'NOTICE', 'CONTRIBUTING.md',
                'SECURITY.md', 'CODE_OF_CONDUCT.md', 'CHANGELOG.md', '.github/workflows/ci.yml']
    for name in required:
        assert (ROOT / name).is_file(), name
    broken = []
    for p in public_files():
        if p.suffix == '.md':
            for target in re.findall(r'\[[^\]]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)', p.read_text()):
                if re.match(r'(?:https?://|mailto:|#)', target):
                    continue
                target = target.split('#', 1)[0]
                if target and not (p.parent / target).exists():
                    broken.append(f'{p.relative_to(ROOT)} -> {target}')
        if p.suffix == '.sh':
            subprocess.run(['bash', '-n', str(p)], check=True)
    assert not broken, '\n'.join(broken)
    assert compileall.compile_dir(ROOT / 'scripts', quiet=1)
    contract_path = ROOT / ('release.yaml' if (ROOT / 'release.yaml').exists() else 'contracts/release.yaml')
    contract = yaml.safe_load(contract_path.read_text())
    evidence = json.loads((ROOT / contract.get('validation_report', 'validation/preview.10.json')).read_text())
    assert contract['release_version'] == evidence['release']
    for suite in evidence['suites'].values():
        assert suite['failed'] == 0 and suite['passed'] == len(suite['cases'])
        assert all(c['error'] is None and c['status'] in c['expected_statuses'] for c in suite['cases'])
    for artifact in contract['images']:
        assert artifact['reference'].endswith('@' + artifact['digest'])
        assert (ROOT / artifact['report']).is_file()
        if evidence.get('images'):
            assert evidence['images'][artifact['platform']] == artifact['digest']
            assert artifact['patch_digest'] == evidence['patch_digest']
    if (ROOT / 'patches').is_dir():
        checksums = json.loads((ROOT / 'patches/checksums.json').read_text())
        series = [x for x in (ROOT / 'patches/series').read_text().splitlines() if x and not x.startswith('#')]
        assert set(series) == set(checksums)
        for name in series:
            assert Path(name).name == name
            assert hashlib.sha256((ROOT / 'patches' / name).read_bytes()).hexdigest() == checksums[name]
        # A reviewed stable release can remain available while new source is
        # accepted as an explicit candidate. Never attribute its older evidence
        # to the current patch set.
        source_contract = contract
        candidate_path = ROOT / 'release.candidate.yaml'
        if candidate_path.exists():
            source_contract = yaml.safe_load(candidate_path.read_text())
            assert source_contract['status'] == 'candidate'
            assert source_contract['upstream'] == contract['upstream']
            candidate_evidence = json.loads((ROOT / source_contract['validation_report']).read_text())
            assert candidate_evidence['patch_digest'] == checksums['0001-native-multimodal.patch']
            assert candidate_evidence['failed'] == 0
            assert candidate_evidence['passed'] == len(candidate_evidence['cases'])
            assert all(c['error'] is None and c['status'] in c['expected_statuses'] for c in candidate_evidence['cases'])
            for artifact in source_contract['images']:
                assert artifact['patch_digest'] == checksums['0001-native-multimodal.patch']
                assert artifact['reference'].endswith('@' + artifact['digest'])
                assert artifact['acceptance'] == 'tested-with-mock'
                assert artifact['report'] == source_contract['validation_report']
        assert source_contract['patch_set']['checksums'] == checksums
        assert contract['upstream']['commit'] == json.loads((ROOT / 'upstream.lock.json').read_text())['commit']
    print('Public source, links, shell/Python syntax and release evidence: passed')

if __name__ == '__main__':
    main()
