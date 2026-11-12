#!/usr/bin/env python3
"""Mock GitHub API boundaries; archives really pack and restore locally."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch
import prepare_rollback
from release_archive import pack
from selftest_delivery import Fixture


def main():
    results = []
    for label, change, code in [
        ('已发布可用归档可真实恢复', {}, 0),
        ('首次无发布显式记录无回滚', {'status': 404, 'allow_first': True}, 0),
        ('未许可首次缺失不能跳过', {'status': 404}, 1),
        ('权限错误不能伪装首次', {'status': 403, 'allow_first': True}, 1),
        ('显式标签不存在不能伪装首次', {'status': 404, 'allow_first': True, 'requested': 'verified-missing'}, 1),
        ('草稿不能充当可用旧版', {'draft': True}, 1),
        ('非运行发布不能充当旧版', {'tag': 'documentation-v3'}, 1),
        ('归档必须与tag源码提交一致', {'commit': 'b' * 40}, 1),
        ('归档必须与tag构建ID一致', {'tag': 'verified-wrong-build'}, 1),
        ('指定标签与API结果不符拒绝', {'requested': 'verified-something-else'}, 1),
        ('传输归档损坏拒绝', {'corrupt': True}, 1),
    ]:
        with tempfile.TemporaryDirectory(prefix='sanguo3-release-store-selftest-') as td:
            root = Path(td); f = Fixture(root)
            archive = root / 'release.tar.gz'
            pack(root / 'dist', archive, '/sanguo3/', f.commit, f.build)
            release = {'tag_name': change.get('tag', 'verified-' + f.build), 'draft': change.get('draft', False), 'prerelease': False}
            def fake(args, **kwargs):
                if args[:3] == ['gh', 'api', '--include']:
                    status = change.get('status', 200)
                    return subprocess.CompletedProcess(args, 0 if status == 200 else 1, 'HTTP/2.0 ' + str(status) + '\n\n' + json.dumps(release), '' if status == 200 else 'API error')
                if args[:2] == ['gh', 'api']:
                    return subprocess.CompletedProcess(args, 0, json.dumps({'object': {'type': 'commit', 'sha': change.get('commit', f.commit)}}), '')
                if args[:3] == ['gh', 'release', 'download']:
                    out = Path(args[args.index('--dir') + 1])
                    shutil.copy2(archive, out / archive.name)
                    shutil.copy2(root / 'release.tar.gz.sha256', out / 'release.tar.gz.sha256')
                    if change.get('corrupt'):
                        with (out / archive.name).open('ab') as stream: stream.write(b'corrupt')
                    return subprocess.CompletedProcess(args, 0, '', '')
                raise AssertionError(args)
            argv = ['prepare_rollback.py', '--repo', 'TEST/TEST', '--output', str(root / 'rollback'), '--expected-base', '/sanguo3/']
            if change.get('allow_first'): argv.append('--allow-first-release')
            if change.get('requested'): argv += ['--tag', change['requested']]
            log = io.StringIO()
            with patch.object(sys, 'argv', argv), patch.object(prepare_rollback.subprocess, 'run', fake), patch.dict(os.environ, {'GITHUB_OUTPUT': str(root / 'github-output')}), contextlib.redirect_stdout(log):
                actual = prepare_rollback.main()
            assert actual == code, (label, actual, log.getvalue())
            if code == 0:
                identity = json.loads((root / 'rollback/identity.json').read_text())
                assert identity['available'] is (change.get('status') != 404)
            results.append({'case': label, 'passed': True, 'actualExitCode': actual})
    print(json.dumps({'scope': 'Mock GitHub responses; real local archive IO. No actual GitHub deployment performed.', 'total': len(results), 'passed': len(results), 'failed': 0, 'cases': results}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
