#!/usr/bin/env python3
"""Artificial-fixture tests for delivery tools; never original-game validation."""
from pathlib import Path
import copy
import hashlib
import json
import subprocess
import sys
import tempfile


def main():
    kit = Path(__file__).resolve().parent.parent
    results = []

    def run(name, args, code, contains=None):
        p = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)
        ok = p.returncode == code and (contains is None or contains in p.stdout + p.stderr)
        if not ok:
            raise AssertionError((name, p.returncode, p.stdout, p.stderr))
        results.append({'case': name, 'expectedExitCode': code, 'actualExitCode': p.returncode, 'passed': True})

    with tempfile.TemporaryDirectory(prefix='sanguo3-delivery-selftest-') as td:
        root = Path(td)
        ledger = root / 'ledger'
        ledger.mkdir()
        evidence = root / 'synthetic.txt'
        evidence.write_text('Artificial fixture. Not original evidence, a real game report, or a website.')
        categories = json.loads((kit / 'templates/project.json').read_text())['requiredCoverage']
        project = {
            'schemaVersion': 1, 'target': {'identityStatus': 'confirmed', 'language': 'zh-Hant'},
            'display': {'logicalWidth': 1, 'logicalHeight': 1, 'primaryMode': 'test-only', 'referenceIds': ['TEST-REF']},
            'inventory': {'status': 'confirmed', 'referenceIds': ['TEST-REF']},
            'strictTarget': {'placeholderAllowed': False, 'pixelDifferenceAllowed': 0, 'unknownAllowed': False},
            'requiredCoverage': categories,
            'candidate': {'commit': 'a' * 40, 'buildId': 'synthetic-test', 'basePath': '/sanguo3/'},
        }
        reports = [{'id': 'TEST-' + c, 'category': c, 'buildId': 'synthetic-test', 'commit': 'a' * 40, 'result': 'passed', 'exitCode': 0, 'executed': 1, 'failed': 0, 'skipped': 0, 'artifactPaths': ['synthetic.txt'], 'referenceIds': ['TEST-REF'], **({'diffPixels': 0} if c == 'ui' else {})} for c in categories if c != 'live']
        row = {'referenceIds': ['TEST-REF'], 'caseIds': ['TEST-CASE'], 'reportIds': ['TEST-ui', 'TEST-dynamic'], 'evidenceStatus': 'confirmed', 'implementationStatus': 'implemented', 'comparisonStatus': 'passed'}
        task = lambda i, status, deps: {'id': i, 'title': 'Artificial test task', 'required': True, 'status': status, 'dependsOn': deps, 'acceptance': ['schema fixture only'], 'reportIds': ['TEST-build'] if status == 'done' else [], 'outputPaths': ['synthetic.txt'] if status == 'done' else [], 'blockerIds': []}
        data = {
            'project': project,
            'references': [{'id': 'TEST-REF', 'kind': 'original-rule-observation', 'evidenceStatus': 'confirmed', 'path': 'synthetic.txt', 'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()}],
            'screens': [{'id': 'TEST-SCREEN', **row, 'hasPlaceholder': False, 'pixelMode': 'exact', 'diffPixels': 0, 'dynamicCoverageStatus': 'passed'}],
            'features': [{'id': 'TEST-FEATURE', **row, 'kind': 'rules', 'reportIds': ['TEST-rules']}],
            'reports': reports,
            'tasks': [task('IMPLEMENT', 'done', []), task('RELEASE-EXACT', 'verify', ['IMPLEMENT']), task('OPS-LIVE', 'todo', ['RELEASE-EXACT']), task('FINAL-DELIVERY', 'todo', ['OPS-LIVE'])],
            'unknowns': [],
        }

        def write(d):
            for name, obj in d.items():
                (ledger / (name + '.json')).write_text(json.dumps(obj))

        validator = kit / 'tools/validate_handoff.py'
        command = [validator, '--data', ledger, '--artifact-root', root]
        run('真实初始模板结构通过', [validator, '--data', kit / 'templates'], 0, 'RESULT: PASS')
        run('真实初始模板不能发布', [validator, '--data', kit / 'templates', '--mode', 'exact-release'], 1, 'RESULT: BLOCKED')
        write(data)
        run('发布前门禁不依赖自身先done', [*command, '--mode', 'exact-release'], 0, 'RESULT: PASS')
        stale = copy.deepcopy(data)
        stale['reports'][0]['buildId'] = 'old-build'
        write(stale)
        run('旧构建报告不能借用', [*command, '--mode', 'exact-release'], 1, 'stale or missing report buildId')
        stale['reports'][0]['buildId'] = 'synthetic-test'
        stale['reports'][0]['commit'] = 'b' * 40
        write(stale)
        run('旧提交报告不能借用', [*command, '--mode', 'exact-release'], 1, 'stale or missing report commit')
        write(data)
        run('尚未部署不能通过最终交付', [*command, '--mode', 'delivered'], 1, 'required task not done')
        bad = copy.deepcopy(data)
        bad['tasks'][0]['status'] = 'todo'
        write(bad)
        run('真正实施任务不能借分期跳过', [*command, '--mode', 'exact-release'], 1, 'IMPLEMENT: required task not done')
        data['reports'].append({'id': 'TEST-live', 'category': 'live', 'buildId': 'synthetic-test', 'commit': 'a' * 40, 'result': 'passed', 'exitCode': 0, 'executed': 1, 'failed': 0, 'skipped': 0, 'artifactPaths': ['synthetic.txt'], 'referenceIds': [], 'baseUrl': 'https://example.invalid/sanguo3/', 'expectedBuildId': 'synthetic-test', 'testedBuildId': 'synthetic-test'})
        data['tasks'][1] = task('RELEASE-EXACT', 'done', ['IMPLEMENT'])
        data['tasks'][2] = task('OPS-LIVE', 'done', ['RELEASE-EXACT'])
        data['tasks'][2]['reportIds'] = ['TEST-live']
        data['tasks'][3]['status'] = 'verify'
        write(data)
        run('部署后门禁不依赖最终汇总先done', [*command, '--mode', 'delivered'], 0, 'RESULT: PASS')
        bad = copy.deepcopy(data)
        bad['reports'][-1]['testedBuildId'] = 'wrong-version'
        write(bad)
        run('线上版本不匹配被拒绝', [*command, '--mode', 'delivered'], 1, 'live build identity mismatch')

        dist = root / 'dist'
        dist.mkdir()
        (dist / 'assets').mkdir()
        (dist / 'assets/main.js').write_text('console.log("synthetic tool fixture");')
        (dist / 'index.html').write_text('<!doctype html><script type="module" src="/sanguo3/assets/main.js"></script>')
        manifest = {'schemaVersion': 1, 'commit': 'a' * 40, 'buildId': 'synthetic-test', 'builtAt': '2026-11-12T00:00:00Z', 'basePath': '/sanguo3/', 'entry': 'index.html', 'rulesVersion': 'synthetic-only', 'dataVersion': 'synthetic-only', 'assetsVersion': 'synthetic-only', 'toolchain': {'node': 'test', 'npm': 'test'}, 'files': {}}

        def write_manifest():
            manifest['files'] = {p.relative_to(dist).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in dist.rglob('*') if p.is_file() and p.name != 'release-manifest.json'}
            (dist / 'release-manifest.json').write_text(json.dumps(manifest))

        write_manifest()
        verify = kit / 'tools/verify_dist.py'
        check = [verify, '--dist', dist, '--expected-base', '/sanguo3/', '--github-pages']
        run('完整人工子路径包通过静态检查', check, 0, '"result": "passed"')
        (dist / 'assets/main.js').write_text('changed-after-build')
        run('构建后资源变更被摘要发现', check, 1, 'file digest differs')
        write_manifest()
        (dist / 'unlisted.txt').write_text('not in manifest')
        run('未列出文件阻断发布', check, 1, 'unlisted file')
        (dist / 'unlisted.txt').unlink()
        (dist / 'index.html').write_text('<script src="/assets/main.js"></script>')
        write_manifest()
        run('根路径硬编码在子路径被拒绝', check, 1, 'escapes deployment base')
        (dist / 'index.html').write_text('<script src="https://example.invalid/game.js"></script>')
        write_manifest()
        run('外部运行脚本不冒充完整静态包', check, 1, 'packaged locally')
        (dist / 'index.html').write_text('<script src="/sanguo3/assets/main.js"></script>')
        (dist / 'docs').mkdir()
        (dist / 'docs/private.txt').write_text('test-only forbidden directory')
        write_manifest()
        run('参考文档目录不得混入站点', check, 1, 'non-runtime directory')
        (dist / 'docs/private.txt').unlink()
        (dist / 'docs').rmdir()
        (dist / 'program.md').write_bytes(bytes(0x100) + b'SEGA MEGA DRIVE ' + bytes(256))
        write_manifest()
        run('改后缀的MD程序头也被阻断', check, 1, 'Mega Drive program header')
        (dist / 'program.md').unlink()
        write_manifest()
        manifest['rulesVersion'] = None
        (dist / 'release-manifest.json').write_text(json.dumps(manifest))
        run('空版本不能发布', check, 1, 'rulesVersion')
        run('没有dist不能声明产物完成', [verify, '--dist', root / 'missing'], 1, 'missing')

    print(json.dumps({'scope': 'Artificial fixtures for tools only; no game or website tested', 'total': len(results), 'passed': len(results), 'failed': 0, 'cases': results}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
