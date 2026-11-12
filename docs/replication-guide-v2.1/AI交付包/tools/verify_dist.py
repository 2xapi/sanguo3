#!/usr/bin/env python3
"""Read-only static release checks. Does not run or certify the game."""
from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import argparse
import hashlib
import json
import re


class EntryAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in {'script', 'img', 'audio', 'video', 'source', 'track', 'iframe'} and a.get('src'):
            self.urls.append(a['src'])
        if tag == 'video' and a.get('poster'):
            self.urls.append(a['poster'])
        if tag == 'link' and set(a.get('rel', '').lower().split()) & {'stylesheet', 'modulepreload', 'preload', 'icon'} and a.get('href'):
            self.urls.append(a['href'])


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def validate(root, expected_base=None, github_pages=False):
    errors = []

    def check(ok, message):
        if not ok:
            errors.append(message)
        return bool(ok)

    def relpath(value):
        return isinstance(value, str) and bool(value) and '\\' not in value and not PurePosixPath(value).is_absolute() and all(x not in {'', '.', '..'} for x in value.split('/'))

    if not root.is_dir():
        return ['dist directory is missing; no application build was verified'], {}
    manifest_path = root / 'release-manifest.json'
    try:
        m = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return [f'release-manifest.json cannot be read: {exc}'], {}
    if not isinstance(m, dict):
        return ['release manifest must be an object'], {}
    check(type(m.get('schemaVersion')) is int and m['schemaVersion'] == 1, 'schemaVersion must be 1')
    check(isinstance(m.get('commit'), str) and bool(re.fullmatch('[0-9a-f]{40}', m['commit'])), 'full source commit is required')
    for name in ['buildId', 'builtAt', 'rulesVersion', 'dataVersion', 'assetsVersion']:
        check(isinstance(m.get(name), str) and bool(m[name].strip()) and m[name] not in {'unknown', 'pending', '待确认'}, f'{name} must be a nonempty actual version/value')
    tools = m.get('toolchain')
    check(isinstance(tools, dict) and all(isinstance(tools.get(k), str) and tools[k] for k in ['node', 'npm']), 'toolchain.node and toolchain.npm are required')
    base = m.get('basePath')
    base_valid = isinstance(base, str) and bool(re.fullmatch(r'/(?:[A-Za-z0-9._-]+/)*', base)) and all(p not in {'.', '..'} for p in base.split('/'))
    check(base_valid, 'basePath must be a normalized absolute directory URL path')
    if expected_base is not None:
        check(base == expected_base, 'build basePath differs from expected deployment base')
    check(m.get('entry') == 'index.html', 'entry must be index.html')
    files = m.get('files')
    if not check(isinstance(files, dict) and bool(files), 'files must map every release file to a SHA-256'):
        return errors, m
    safe_files = {}
    for rel, sha in files.items():
        if not check(relpath(rel), f'invalid release file path: {rel!r}'):
            continue
        check(rel != 'release-manifest.json', 'manifest must not recursively hash itself')
        check(isinstance(sha, str) and bool(re.fullmatch('[0-9a-f]{64}', sha)), f'invalid SHA-256: {rel}')
        safe_files[rel] = sha
    check('index.html' in safe_files, 'index.html is not listed in files')
    actual = set()
    forbidden = {'.git', '.github', 'node_modules', 'reference', 'attachments', 'docs'}
    for p in root.rglob('*'):
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            errors.append(f'symlinks are not deployable release files: {rel}')
            continue
        if not p.is_file():
            continue
        if rel == 'release-manifest.json':
            continue
        actual.add(rel)
        check(not forbidden.intersection(p.relative_to(root).parts), f'non-runtime directory mixed into release: {rel}')
        if github_pages:
            check(p.stat().st_size < 100 * 1024 * 1024, f'file exceeds conservative Pages upload limit: {rel}')
        with p.open('rb') as f:
            signature = f.read(512)
        check(not signature[0x100:0x110].startswith(b'SEGA'), f'Mega Drive program header found in release: {rel}')
    if github_pages:
        total = sum((root / p).stat().st_size for p in actual)
        check(total < 1024 * 1024 * 1024, 'release exceeds conservative 1 GiB Pages site budget')
    for rel in sorted(set(safe_files) - actual):
        errors.append(f'manifest file is missing: {rel}')
    for rel in sorted(actual - set(safe_files)):
        errors.append(f'unlisted file in dist: {rel}')
    for rel in sorted(actual & set(safe_files)):
        check(digest(root / rel) == safe_files[rel], f'file digest differs from manifest: {rel}')
    entry = root / 'index.html'
    if entry.is_file() and not entry.is_symlink():
        try:
            parser = EntryAssets()
            parser.feed(entry.read_text(encoding='utf-8'))
            for url in parser.urls:
                parsed = urlsplit(url)
                if parsed.scheme == 'data':
                    continue
                if parsed.scheme or parsed.netloc:
                    errors.append(f'entry runtime asset must be packaged locally: {url}')
                    continue
                raw = unquote(parsed.path)
                if not raw:
                    continue
                if raw.startswith('/'):
                    if not base_valid or not raw.startswith(base):
                        errors.append(f'entry asset escapes deployment base: {url}')
                        continue
                    raw = raw[len(base):]
                while raw.startswith('./'):
                    raw = raw[2:]
                if not relpath(raw):
                    errors.append(f'unsafe or unsupported entry asset URL: {url}')
                else:
                    check(raw in safe_files, f'entry asset missing from manifest: {url}')
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f'entry HTML cannot be checked: {exc}')
    return errors, m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dist', type=Path, default=Path('dist'))
    p.add_argument('--expected-base')
    p.add_argument('--github-pages', action='store_true')
    a = p.parse_args()
    errors, m = validate(a.dist.resolve(), a.expected_base, a.github_pages)
    print(json.dumps({'result': 'blocked' if errors else 'passed', 'buildId': m.get('buildId'), 'errors': errors, 'scope': 'static package consistency only; browser behavior and original fidelity are not certified'}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
