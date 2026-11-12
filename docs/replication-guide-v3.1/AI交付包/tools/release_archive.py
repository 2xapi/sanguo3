#!/usr/bin/env python3
"""Pack or restore a complete verified dist, with no rebuild and no overwrites."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile
from verify_dist import validate

LIMIT = 1024 * 1024 * 1024


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def verified(root, base, commit=None, build=None):
    errors, manifest = validate(root, base, True)
    if commit is not None and manifest.get('commit') != commit:
        errors.append('archive commit differs from expected')
    if build is not None and manifest.get('buildId') != build:
        errors.append('archive buildId differs from expected')
    if errors:
        raise ValueError('; '.join(errors))
    return manifest


def pack(dist, output, base, commit, build):
    manifest = verified(dist, base, commit, build)
    checksum = output.with_name(output.name + '.sha256')
    if output.exists() or checksum.exists():
        raise ValueError('archive/checksum already exists; never overwrite a release')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Temporary archive prevents a partial write from appearing as a usable release.
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.pack-') as td:
        tmp = Path(td) / 'release.tar.gz'
        with tarfile.open(tmp, 'w:gz') as tar:
            for path in sorted(dist.rglob('*')):
                if path.is_file():
                    tar.add(path, arcname=path.relative_to(dist).as_posix(), recursive=False)
        # Detect a change during archiving, including changes to the manifest itself.
        with tempfile.TemporaryDirectory(prefix='archive-roundtrip-') as rd:
            restore(tmp, digest(tmp), Path(rd) / 'dist', base, commit, build)
        os.link(tmp, output)
        checksum.write_text(digest(output) + '  ' + output.name + '\n', encoding='ascii')
    return manifest


def restore(archive, expected_sha, output, base, commit=None, build=None):
    if not isinstance(expected_sha, str) or not re.fullmatch('[a-f0-9]{64}', expected_sha) or digest(archive) != expected_sha:
        raise ValueError('archive SHA-256 mismatch')
    if output.exists() or output.is_symlink():
        raise ValueError('restore target already exists; use a new directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='.restore-') as td:
        root, seen, total = Path(td), set(), 0
        with tarfile.open(archive, 'r:gz') as tar:
            for member in tar:
                rel = member.name
                parts = rel.split('/')
                if (not rel or '\\' in rel or PurePosixPath(rel).is_absolute()
                        or any(p in {'', '.', '..'} for p in parts) or rel in seen
                        or not (member.isdir() or member.isfile())):
                    raise ValueError('unsafe or duplicate archive member: ' + rel)
                seen.add(rel)
                total += member.size
                if total > LIMIT or member.size < 0:
                    raise ValueError('archive exceeds release size budget')
                path = root / rel
                if member.isdir():
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with tar.extractfile(member) as src, path.open('xb') as dst:
                        shutil.copyfileobj(src, dst)
        manifest = verified(root, base, commit, build)
        root.rename(output)
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='operation', required=True)
    a = sub.add_parser('pack')
    a.add_argument('--dist', type=Path, required=True)
    a.add_argument('--output', type=Path, required=True)
    a.add_argument('--expected-commit', required=True)
    a.add_argument('--expected-build-id', required=True)
    b = sub.add_parser('restore')
    b.add_argument('--archive', type=Path, required=True)
    b.add_argument('--checksum-file', type=Path, required=True)
    b.add_argument('--output', type=Path, required=True)
    b.add_argument('--expected-commit')
    b.add_argument('--expected-build-id', required=True)
    for item in [a, b]:
        item.add_argument('--expected-base', required=True)
    args = p.parse_args()
    try:
        if args.operation == 'pack':
            m = pack(args.dist.resolve(), args.output.absolute(), args.expected_base, args.expected_commit, args.expected_build_id)
        else:
            line = args.checksum_file.read_text(encoding='ascii').strip()
            match = re.fullmatch(r'([a-f0-9]{64})  (.+)', line)
            if not match or match[2] != args.archive.name:
                raise ValueError('checksum must name this exact archive')
            m = restore(args.archive, match[1], args.output.absolute(), args.expected_base, args.expected_commit, args.expected_build_id)
        print(json.dumps({'result': 'passed', 'operation': args.operation, 'commit': m['commit'], 'buildId': m['buildId'], 'basePath': m['basePath']}))
        return 0
    except (OSError, ValueError, tarfile.TarError, EOFError) as exc:
        print(json.dumps({'result': 'blocked', 'error': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
