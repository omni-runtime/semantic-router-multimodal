#!/usr/bin/env python3
"""Extract verified native/system libraries from a locked OCI platform.

Used only by the cross-build container. Absolute image symlinks are rewritten
inside the destination; archive entries cannot escape it. No image is executed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--base-digest', required=True)
    p.add_argument('--platform', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    root = a.output.resolve()
    if any(root.iterdir()):
        p.error('destination must be empty; do not merge library generations')
    os_name, arch = a.platform.split('/')
    records = []
    with tarfile.open(a.archive) as archive:
        def blob(desc):
            value = desc['digest']
            if not value.startswith('sha256:') or len(value) != 71:
                raise ValueError('invalid OCI digest')
            return 'blobs/sha256/' + value[7:]

        def document(desc):
            data = archive.extractfile(blob(desc)).read()
            if len(data) != desc['size'] or 'sha256:' + hashlib.sha256(data).hexdigest() != desc['digest']:
                raise ValueError('OCI descriptor mismatch')
            return json.loads(data)

        index = json.load(archive.extractfile('index.json'))
        candidates = [d for d in index['manifests'] if d['digest'] == a.base_digest]
        if len(candidates) != 1:
            raise ValueError('archive does not identify the locked base')
        selected = candidates[0]
        manifest = document(selected)
        while 'manifests' in manifest:
            candidates = [d for d in manifest['manifests'] if d.get('platform', {}).get('os') == os_name and d.get('platform', {}).get('architecture') == arch]
            if len(candidates) != 1:
                raise ValueError('missing or ambiguous platform')
            selected = candidates[0]
            manifest = document(selected)
        config = document(manifest['config'])
        if (config['os'], config['architecture']) != (os_name, arch):
            raise ValueError('platform differs from requested build')
        for desc in manifest['layers']:
            with archive.extractfile(blob(desc)) as stream:
                if 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest() != desc['digest']:
                    raise ValueError('layer digest mismatch')
            with tarfile.open(fileobj=archive.extractfile(blob(desc)), mode='r|*') as layer:
                for member in layer:
                    name = member.name.removeprefix('./')
                    path = PurePosixPath(name)
                    if path.is_absolute() or '..' in path.parts:
                        raise ValueError('unsafe image path')
                    if not any(name == prefix or name.startswith(prefix + '/') for prefix in ('app/lib', 'lib', 'lib64', 'usr/lib', 'usr/lib64')):
                        continue
                    target = root.joinpath(*path.parts)
                    if not target.parent.resolve().is_relative_to(root):
                        raise ValueError('image link escaped the destination')
                    if path.name.startswith('.wh.'):
                        victim = target.parent / path.name[4:]
                        if path.name == '.wh..wh..opq':
                            for child in target.parent.iterdir():
                                if child.is_dir() and not child.is_symlink(): shutil.rmtree(child)
                                else: child.unlink()
                        elif victim.is_dir() and not victim.is_symlink(): shutil.rmtree(victim)
                        else: victim.unlink(missing_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if member.isdir():
                        target.mkdir(exist_ok=True)
                    elif member.issym():
                        linked = Path(member.linkname)
                        destination = root / str(linked).lstrip('/') if linked.is_absolute() else target.parent / linked
                        if not destination.resolve().is_relative_to(root):
                            raise ValueError('unsafe image symlink')
                        if target.is_symlink() or target.is_file(): target.unlink()
                        target.symlink_to(os.path.relpath(destination, target.parent))
                    elif member.isfile():
                        if target.is_symlink(): target.unlink()
                        with layer.extractfile(member) as source, target.open('wb') as output:
                            shutil.copyfileobj(source, output)
                        target.chmod(member.mode & 0o777)
                        records.append({'path': name, 'bytes': member.size})
                    elif member.islnk():
                        source = root / member.linkname.removeprefix('./')
                        if not source.resolve().is_relative_to(root): raise ValueError('unsafe hard link')
                        if target.exists() or target.is_symlink(): target.unlink()
                        os.link(source, target)
        report = {'base_digest': a.base_digest, 'platform': a.platform,
                  'manifest_digest': selected['digest'], 'extracted_files': records}
        (root / 'extraction.json').write_text(json.dumps(report, indent=2) + '\n')
        print(f'Verified {a.platform} library extraction: {len(records)} files')


if __name__ == '__main__':
    main()
