#!/usr/bin/env python3
"""Download a published verified release and validate its source tag and full dist."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
from urllib.parse import quote
from release_archive import restore


def gh(*args):
    p = subprocess.run(['gh', *args], text=True, capture_output=True)
    if p.returncode:
        raise ValueError('GitHub CLI failed: ' + p.stderr.strip())
    return p.stdout


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY'), required=not bool(os.environ.get('GITHUB_REPOSITORY')))
    p.add_argument('--tag', help='Omit to choose GitHub latest published release')
    p.add_argument('--allow-first-release', action='store_true')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--expected-base', required=True)
    a = p.parse_args()
    try:
        if a.output.exists():
            raise ValueError('rollback output already exists')
        endpoint = 'repos/' + a.repo + '/releases/' + ('tags/' + quote(a.tag, safe='') if a.tag else 'latest')
        response = subprocess.run(['gh', 'api', '--include', endpoint], text=True, capture_output=True)
        if response.returncode:
            # Only an explicit 404 for latest can mean a genuinely new site.
            # Permission errors, transient failures and an explicit missing tag must abort.
            if not a.tag and a.allow_first_release and re.match(r'HTTP/[0-9.]+ 404\b', response.stdout):
                a.output.mkdir(parents=True)
                (a.output / 'identity.json').write_text(json.dumps({'available': False, 'reason': 'no published release; no automatic rollback possible'}))
                if os.environ.get('GITHUB_OUTPUT'):
                    with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
                        out.write('available=false\n')
                print('FIRST RELEASE: no previous release to restore')
                return 0
            raise ValueError('Cannot select a verified rollback release: ' + response.stderr.strip())
        release = json.loads(response.stdout[response.stdout.index('{'):])
        tag = release['tag_name']
        if a.tag and tag != a.tag:
            raise ValueError('Release response differs from requested tag')
        if release['draft'] or release['prerelease'] or not re.fullmatch(r'verified-[A-Za-z0-9._-]+', tag):
            raise ValueError('Selected release is not a published verified runtime release')
        obj = json.loads(gh('api', 'repos/' + a.repo + '/git/ref/tags/' + quote(tag, safe='')))['object']
        for _ in range(8):
            if obj['type'] == 'commit':
                break
            if obj['type'] != 'tag':
                raise ValueError('Unexpected tag object')
            obj = json.loads(gh('api', 'repos/' + a.repo + '/git/tags/' + obj['sha']))['object']
        if obj['type'] != 'commit':
            raise ValueError('Cannot resolve source commit')
        a.output.mkdir(parents=True)
        gh('release', 'download', tag, '--repo', a.repo, '--pattern', 'release.tar.gz', '--pattern', 'release.tar.gz.sha256', '--dir', str(a.output))
        checksum = (a.output / 'release.tar.gz.sha256').read_text(encoding='ascii').strip()
        match = re.fullmatch(r'([a-f0-9]{64})  release.tar.gz', checksum)
        if not match:
            raise ValueError('Missing or malformed archive checksum')
        manifest = restore(a.output / 'release.tar.gz', match[1], a.output / 'dist', a.expected_base, obj['sha'], tag[len('verified-'):])
        identity = {'available': True, 'tag': tag, 'commit': manifest['commit'], 'buildId': manifest['buildId'], 'basePath': manifest['basePath']}
        (a.output / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
                out.write('available=true\nbuild_id=' + manifest['buildId'] + '\ncommit=' + manifest['commit'] + '\ntag=' + tag + '\n')
        print(json.dumps(identity))
        return 0
    except (OSError, ValueError, KeyError, tarfile.TarError, EOFError) as exc:
        print(json.dumps({'result': 'blocked', 'error': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
