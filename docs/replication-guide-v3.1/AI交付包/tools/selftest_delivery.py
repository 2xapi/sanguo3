#!/usr/bin/env python3
"""Adversarial tool fixtures only. No actual game, original footage or live site."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from PIL import Image

KIT = Path(__file__).resolve().parent.parent
TOOLS = KIT / 'tools'
CATEGORIES = json.loads((KIT / 'templates/project.json').read_text())['requiredCoverage']
RESULTS = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def command(name, args, expected=0, contains=None):
    env = {k: v for k, v in os.environ.items() if k not in ['TRUSTED_SCOPE_SHA256', 'EXPECTED_CANDIDATE_COMMIT', 'EXPECTED_CANDIDATE_BUILD_ID']}
    p = subprocess.run([sys.executable, *map(str, args)], text=True, capture_output=True, env=env)
    assert p.returncode == expected and (contains is None or contains in p.stdout + p.stderr), (name, p.returncode, p.stdout, p.stderr)
    RESULTS.append({'case': name, 'passed': True, 'expectedExitCode': expected, 'actualExitCode': p.returncode})


class Fixture:
    def __init__(self, root, delivered=False):
        self.root, self.ledger = root, root / 'ledger'
        self.commit, self.build = 'a' * 40, 'synthetic-test'
        self.url = 'https://example.invalid/sanguo3/'
        Image.new('RGBA', (2, 2), (0, 0, 0, 255)).save(root / 'original.png')
        Image.new('RGBA', (2, 2), (0, 0, 0, 255)).save(root / 'capture.png')
        dist = root / 'dist'; (dist / 'assets').mkdir(parents=True)
        (dist / 'index.html').write_text('<script src="/sanguo3/assets/main.js"></script>')
        (dist / 'assets/main.js').write_text('console.log("artificial fixture only");')
        self.manifest = {'schemaVersion': 1, 'commit': self.commit, 'buildId': self.build, 'builtAt': '2026-11-12T00:00:00Z', 'basePath': '/sanguo3/', 'entry': 'index.html', 'rulesVersion': 'synthetic-only', 'dataVersion': 'synthetic-only', 'assetsVersion': 'synthetic-only', 'toolchain': {'node': 'test', 'npm': 'test'}}
        self.dist_manifest()
        (root / 'synthetic.bin').write_bytes(b'Artificial fixture only')
        ref = {'id': 'TEST-REF', 'kind': 'original-screen', 'evidenceStatus': 'confirmed', 'path': 'original.png', 'sha256': sha(root / 'original.png'), 'captureQuality': 'native-unscaled'}
        rom_ref = {'id': 'TEST-ROM', 'kind': 'original-data', 'evidenceStatus': 'confirmed', 'path': 'synthetic.bin', 'sha256': sha(root / 'synthetic.bin')}
        target = {'identityStatus': 'confirmed', 'language': 'zh', 'observedScript': 'mixed', 'scriptPolicy': 'preserve-original-mixed-glyphs', 'binarySha256': rom_ref['sha256'], 'baselineId': 'SYNTHETIC-NOT-ORIGINAL', 'referenceIds': ['TEST-ROM']}
        display = {'logicalWidth': 2, 'logicalHeight': 2, 'primaryMode': 'artificial-test', 'referenceIds': ['TEST-REF']}
        inventory = {'status': 'confirmed', 'referenceIds': ['TEST-REF']}
        policy = {'placeholderAllowed': False, 'pixelDifferenceAllowed': 0, 'unknownAllowed': False}
        project = {'schemaVersion': 2, 'target': target, 'display': display, 'inventory': inventory, 'strictTarget': policy, 'requiredCoverage': CATEGORIES,
                   'candidate': {'commit': self.commit, 'buildId': self.build, 'baseUrl': self.url, 'basePath': '/sanguo3/', 'manifestPath': 'dist/release-manifest.json'}}
        cases, scope_cases = [], {}
        self.raw, self.observations = {}, {}
        for category in CATEGORIES:
            cid = 'CASE-' + category
            refs = ['TEST-REF'] if category in {'ui', 'dynamic', 'interaction', 'rules', 'data', 'ai', 'random', 'audio'} else []
            assertions = [{'id': 'VALUE', 'op': 'equals', 'expected': 7}]
            obs = {'value': 7, 'buildId': self.build, 'commit': self.commit, 'baseUrl': self.url}
            out = [{'id': 'VALUE', 'status': 'passed', 'actualFrom': {'path': category + '-observation.json', 'pointer': '/value'}}]
            if category == 'ui':
                assertions = [{'id': 'PIXELS', 'op': 'pixel_equal', 'referencePath': 'original.png', 'referenceSha256': ref['sha256']}]
                out = [{'id': 'PIXELS', 'status': 'passed', 'actualPath': 'capture.png'}]
            if category == 'live':
                assertions = [{'id': key, 'op': 'url_equal' if key == 'baseUrl' else 'equals', 'expectedFrom': source} for key, source in [('commit', 'candidate.commit'), ('buildId', 'candidate.buildId'), ('baseUrl', 'deployment.baseUrl')]]
                out = [{'id': a['id'], 'status': 'passed', 'actualFrom': {'path': 'live-observation.json', 'pointer': '/' + a['id']}} for a in assertions]
            spec = {'caseId': cid, 'category': category, 'referenceIds': refs, 'assertions': assertions}
            sp = 'specs/' + cid + '.json'; save(root / sp, spec)
            row = {'id': cid, 'category': category, 'specificationPath': sp, 'specificationSha256': sha(root / sp), 'referenceIds': refs, 'reportIds': ['REPORT-' + category] if delivered or category != 'live' else []}
            cases.append(row); scope_cases[cid] = {k: row[k] for k in ['category', 'specificationPath', 'specificationSha256']}
            self.observations[category] = obs
            self.raw[category] = {'reportId': 'REPORT-' + category, 'buildId': self.build, 'commit': self.commit, 'runner': 'synthetic fixture only', 'command': ['python', 'synthetic.py'], 'exitCode': 0,
                                  'results': [{'caseId': cid, 'status': 'passed', 'assertions': out}], 'artifacts': []}
            if category == 'live':
                self.raw[category].update(expectedBuildId=self.build, testedBuildId=self.build, baseUrl=self.url)
        base_row = {'referenceIds': ['TEST-REF'], 'evidenceStatus': 'confirmed', 'implementationStatus': 'implemented', 'comparisonStatus': 'passed'}
        screen = {'id': 'SCREEN', **base_row, 'caseIds': ['CASE-ui', 'CASE-dynamic', 'CASE-interaction'], 'reportIds': ['REPORT-ui', 'REPORT-dynamic', 'REPORT-interaction'], 'hasPlaceholder': False}
        feature = {'id': 'FEATURE', **base_row, 'caseIds': ['CASE-rules'], 'reportIds': ['REPORT-rules'], 'kind': 'rules'}
        def task(ident, phase, status, deps, case_ids):
            return {'id': ident, 'phase': phase, 'status': status, 'required': True, 'dependsOn': deps, 'acceptance': ['Artificial fixture only'], 'caseIds': case_ids,
                    'reportIds': ['REPORT-' + c[5:] for c in case_ids] if status == 'done' else [], 'outputPaths': ['dist/index.html'] if status == 'done' else [], 'blockerIds': []}
        tasks = [task('OPS-PREP', 'bootstrap', 'done', [], ['CASE-bootstrap']),
                 task('IMPLEMENT', 'implementation', 'done', ['OPS-PREP'], ['CASE-' + c for c in CATEGORIES if c not in ['live', 'bootstrap']]),
                 task('RELEASE-EXACT', 'release_gate', 'done' if delivered else 'verify', ['IMPLEMENT'], []),
                 task('OPS-LIVE', 'post_deploy', 'done' if delivered else 'todo', ['RELEASE-EXACT'], ['CASE-live']),
                 task('FINAL-DELIVERY', 'final_gate', 'verify' if delivered else 'todo', ['OPS-LIVE'], [])]
        self.data = {'project': project, 'references': [ref, rom_ref], 'screens': [screen], 'features': [feature], 'cases': cases, 'reports': [], 'tasks': tasks, 'unknowns': []}
        self.data['scope'] = {'schemaVersion': 1, 'status': 'frozen', 'baselineId': target['baselineId'], **{k: copy.deepcopy(project[k]) for k in ['target', 'display', 'inventory', 'strictTarget', 'requiredCoverage']}, 'deployment': {'baseUrl': self.url, 'basePath': '/sanguo3/'},
                              'references': {'TEST-REF': {k: ref[k] for k in ['path', 'sha256', 'kind', 'captureQuality']}, 'TEST-ROM': {k: rom_ref[k] for k in ['path', 'sha256', 'kind']}}, 'screens': {'SCREEN': {k: screen[k] for k in ['caseIds', 'referenceIds']}}, 'features': {'FEATURE': {k: feature[k] for k in ['caseIds', 'referenceIds', 'kind']}}, 'cases': scope_cases,
                              'tasks': {t['id']: {k: t[k] for k in ['phase', 'required', 'dependsOn', 'acceptance', 'caseIds']} for t in tasks}}
        self.selected = [c for c in CATEGORIES if delivered or c != 'live']
        self.flush()
        self.anchor = sha(self.ledger / 'scope.json')
        if delivered:
            save(root / 'release-gate.json', {'result': 'passed', 'mode': 'exact-release', 'scopeSha256': self.anchor, 'commit': self.commit, 'buildId': self.build})
            tasks[2]['outputPaths'] = ['release-gate.json']; self.flush()

    def dist_manifest(self):
        self.manifest['files'] = {p.relative_to(self.root / 'dist').as_posix(): sha(p) for p in (self.root / 'dist').rglob('*') if p.is_file() and p.name != 'release-manifest.json'}
        save(self.root / 'dist/release-manifest.json', self.manifest)

    def flush(self):
        self.data['reports'] = []
        for c in self.selected:
            save(self.root / (c + '-observation.json'), self.observations[c])
            artifacts = [c + '-observation.json'] + (['capture.png'] if c == 'ui' else [])
            self.raw[c]['artifacts'] = [{'path': p, 'sha256': sha(self.root / p)} for p in artifacts]
            report_path = 'reports/' + c + '.json'; save(self.root / report_path, self.raw[c])
            self.data['reports'].append({'id': 'REPORT-' + c, 'path': report_path, 'sha256': sha(self.root / report_path)})
        for name, value in self.data.items():
            save(self.ledger / (name + '.json'), value)

    def args(self, mode='exact-release'):
        return [TOOLS / 'validate_handoff.py', '--data', self.ledger, '--artifact-root', self.root, '--mode', mode,
                '--scope-sha256', self.anchor, '--expected-commit', self.commit, '--expected-build-id', self.build]


def scenario(name, mutate=None, delivered=False, contains=None):
    with tempfile.TemporaryDirectory(prefix='sanguo3-tool-selftest-') as td:
        f = Fixture(Path(td), delivered)
        if mutate:
            mutate(f); f.flush()
        command(name, f.args('delivered' if delivered else 'exact-release'), 1 if mutate else 0, contains or ('RESULT: BLOCKED' if mutate else 'RESULT: PASS'))


def main():
    validator = TOOLS / 'validate_handoff.py'
    command('初始结构可检查', [validator, '--data', KIT / 'templates'], 0, 'RESULT: PASS')
    command('未取证模板禁止发布', [validator, '--data', KIT / 'templates', '--mode', 'exact-release'], 1, 'RESULT: BLOCKED')
    def change_anchored(f, change):
        change(f)
        f.flush()
        f.anchor = sha(f.ledger / 'scope.json')

    def reject_old_language(f):
        for target in [f.data['project']['target'], f.data['scope']['target']]: target['language'] = 'zh-Hant'

    def reject_wrong_rom(f):
        for target in [f.data['project']['target'], f.data['scope']['target']]: target['binarySha256'] = '0' * 64

    def reject_scaled(f):
        f.data['references'][0]['captureQuality'] = 'scaled-browser'
        f.data['scope']['references']['TEST-REF']['captureQuality'] = 'scaled-browser'

    scenario('禁止强制繁体替代原版混排', lambda f: change_anchored(f, reject_old_language), contains='glyph policy unconfirmed')
    scenario('目标样本摘要需链接原版数据', lambda f: change_anchored(f, reject_wrong_rom), contains='target digest must link')
    scenario('缩放观察图不能用于逐像素验收', lambda f: change_anchored(f, reject_scaled), contains='native-unscaled original screen')
    scenario('发布前无自循环')
    scenario('部署后无最终汇总自循环', delivered=True)
    scenario('旧线上期望和实测同时改旧仍拒绝', lambda f: f.raw['live'].update(expectedBuildId='old', testedBuildId='old'), True, 'live build identity mismatch')
    scenario('同路径其他域名拒绝', lambda f: f.raw['live'].update(baseUrl='https://other.invalid/sanguo3/'), True, 'wrong production origin')
    scenario('实际网页仍为旧版本拒绝', lambda f: f.observations['live'].update(buildId='old'), True, 'actual differs from frozen expected')
    scenario('实际网页提交不符拒绝', lambda f: f.observations['live'].update(commit='b' * 40), True, 'actual differs from frozen expected')
    scenario('实际网页域名不符拒绝', lambda f: f.observations['live'].update(baseUrl='https://other.invalid/sanguo3/'), True, 'URL differs')
    scenario('线上HTTP拒绝', lambda f: f.raw['live'].update(baseUrl='http://example.invalid/sanguo3/'), True)
    scenario('线上子路径变化拒绝', lambda f: f.raw['live'].update(baseUrl='https://example.invalid/'), True)
    scenario('候选身份不得全体退回旧版', lambda f: f.data['project']['candidate'].update(buildId='old'), contains='external buildId')
    scenario('候选站点不能跟随错误报告改写', lambda f: f.data['project']['candidate'].update(baseUrl='https://other.invalid/sanguo3/'), contains='production origin')
    scenario('旧构建报告拒绝', lambda f: f.raw['rules'].update(buildId='old'), contains='stale report buildId')
    scenario('旧提交报告拒绝', lambda f: f.raw['rules'].update(commit='b' * 40), contains='stale report commit')
    scenario('不存在案例引用拒绝', lambda f: f.data['screens'][0]['caseIds'].append('NO-SUCH-CASE'), contains='missing linked caseIds')
    scenario('删除实施任务仅留汇总拒绝', lambda f: (f.data['tasks'].pop(1), f.data['tasks'][1].update(dependsOn=['OPS-PREP'])), contains='inventory differs')
    scenario('删除实际屏幕拒绝', lambda f: f.data['screens'].clear(), contains='inventory differs')
    scenario('删除冻结案例拒绝', lambda f: f.data['cases'].pop(), contains='missing linked caseIds')
    scenario('同时删范围及台账仍受外部摘要阻断', lambda f: f.data['scope']['screens'].clear(), contains='trusted anchor')
    scenario('实施任务不能改成部署后跳过', lambda f: f.data['tasks'][1].update(phase='post_deploy'), contains='frozen task changed phase')
    scenario('实施任务未完成拒绝', lambda f: f.data['tasks'][1].update(status='todo'), contains='required task not done')
    scenario('缺原始案例执行拒绝', lambda f: f.raw['rules'].update(results=[]), contains='zero executed cases')
    scenario('断言结果缺失拒绝', lambda f: f.raw['rules']['results'][0].update(assertions=[]), contains='assertion results incomplete')
    scenario('重复案例执行拒绝', lambda f: f.raw['rules']['results'].append(copy.deepcopy(f.raw['rules']['results'][0])), contains='duplicate selected execution')
    scenario('跳过案例不能算通过', lambda f: f.raw['rules']['results'][0].update(status='skipped'), contains='failed, skipped or unrun')
    scenario('执行器非零退出拒绝', lambda f: f.raw['rules'].update(exitCode=1), contains='runner failed')
    scenario('实际数值错误即使写passed仍拒绝', lambda f: f.observations['rules'].update(value=8), contains='actual differs from frozen expected')
    scenario('手改案例预期拒绝', lambda f: save(f.root / 'specs/CASE-rules.json', {'caseId': 'CASE-rules'}), contains='specification digest mismatch')
    scenario('像素被改仍写零差异拒绝', lambda f: Image.new('RGBA', (2, 2), (1, 0, 0, 255)).save(f.root / 'capture.png'), contains='captured pixels differ')
    scenario('截图尺寸不符拒绝', lambda f: Image.new('RGBA', (3, 2)).save(f.root / 'capture.png'), contains='image size mismatch')
    scenario('原版参考被改拒绝', lambda f: Image.new('RGBA', (2, 2), (9, 0, 0, 255)).save(f.root / 'original.png'), contains='original digest mismatch')
    scenario('未解决事实缺口拒绝', lambda f: f.data['unknowns'].append({'id': 'UNKNOWN', 'status': 'open', 'referenceIds': []}), contains='unresolved original fact')
    scenario('任务依赖循环拒绝', lambda f: f.data['tasks'][0].update(dependsOn=['IMPLEMENT']), contains='dependency cycle')
    scenario('上线报告不能提前放过全部交付', lambda f: f.data['tasks'][3].update(status='todo'), True, 'required task not done')
    scenario('发布收据必须为当前候选', lambda f: save(f.root / 'release-gate.json', {'result': 'passed', 'buildId': 'old'}), True, 'current release gate receipt')
    scenario('候选产物与报告身份不符拒绝', lambda f: (f.manifest.update(buildId='old'), f.dist_manifest()), contains='runtime manifest differs')
    scenario('构建后文件变化拒绝', lambda f: (f.root / 'dist/assets/main.js').write_text('changed'), contains='file digest differs')
    scenario('高位深截图不得静默量化', lambda f: Image.new('I;16', (2, 2), 0).save(f.root / 'capture.png'), contains='unsupported image mode')
    scenario('像素自比较拒绝', lambda f: ((f.root / 'capture.png').unlink(), (f.root / 'capture.png').hardlink_to(f.root / 'original.png')), contains='cannot be compared with itself')
    with tempfile.TemporaryDirectory(prefix='sanguo3-corruption-selftest-') as td:
        f = Fixture(Path(td))
        path = f.root / 'reports/rules.json'
        path.write_text(path.read_text().replace('synthetic-test', 'tampered'))
        command('原始报告摘要不符拒绝', f.args(), 1, 'report digest mismatch')
        f.flush()
        (f.root / 'rules-observation.json').write_text('{"value": 99}')
        command('实际输出摘要不符拒绝', f.args(), 1, 'artifact digest mismatch')
        f.flush()
        command('缺外部构建身份拒绝', f.args()[:-4], 1, 'external expected commit required')
        f.flush()
        (f.ledger / 'project.json').write_text('{"schemaVersion": 2, "schemaVersion": 2}')
        command('重复JSON键拒绝', f.args(), 1, 'duplicate JSON key')
    with tempfile.TemporaryDirectory(prefix='sanguo3-dist-pixels-selftest-') as td:
        f = Fixture(Path(td))
        verify = [TOOLS / 'verify_dist.py', '--dist', f.root / 'dist', '--expected-base', '/sanguo3/', '--github-pages']
        command('人工运行包静态检查', verify)
        (f.root / 'dist/index.html').write_text('<script src="/assets/main.js"></script>'); f.dist_manifest()
        command('子路径根引用错误拒绝', verify, 1, 'escapes deployment base')
        (f.root / 'dist/index.html').write_text('<script src="https://example.invalid/x.js"></script>'); f.dist_manifest()
        command('外部运行依赖拒绝', verify, 1, 'packaged locally')
        (f.root / 'dist/index.html').write_text('<script src="/sanguo3/assets/main.js"></script>')
        (f.root / 'dist/program.md').write_bytes(bytes(0x100) + b'SEGA MEGA DRIVE ' + bytes(256)); f.dist_manifest()
        command('改后缀ROM仍拒绝', verify, 1, 'Mega Drive program header')
        (f.root / 'dist/program.md').unlink(); f.dist_manifest()
        (f.root / 'dist/unlisted.txt').write_text('unlisted')
        command('未入清单运行文件拒绝', verify, 1, 'unlisted file')
        command('产物缺失拒绝', [TOOLS / 'verify_dist.py', '--dist', f.root / 'missing'], 1, 'missing')
        compare = [TOOLS / 'compare_pixels.py', '--reference', f.root / 'original.png', '--actual', f.root / 'capture.png', '--out', f.root / 'compare-ok']
        command('独立PNG比较人工同图通过', compare)
        Image.new('RGBA', (2, 2), (1, 0, 0, 255)).save(f.root / 'capture.png')
        compare[-1] = f.root / 'compare-diff'
        command('独立PNG比较检出人工差异', compare, 1, 'failed')
        Image.new('I;16', (2, 2), 0).save(f.root / 'capture.png')
        compare[-1] = f.root / 'compare-depth'
        command('独立PNG比较拒绝高位深', compare, 2, 'bit depth')
    with tempfile.TemporaryDirectory(prefix='sanguo3-archive-selftest-') as td:
        root = Path(td); f = Fixture(root)
        pack = [TOOLS / 'release_archive.py', 'pack', '--dist', root / 'dist', '--output', root / 'release.tar.gz', '--expected-base', '/sanguo3/', '--expected-commit', f.commit, '--expected-build-id', f.build]
        command('完整产物可归档并自检', pack)
        command('发布归档不能覆写', pack, 1, 'already exists')
        restore = [TOOLS / 'release_archive.py', 'restore', '--archive', root / 'release.tar.gz', '--checksum-file', root / 'release.tar.gz.sha256', '--output', root / 'restored', '--expected-base', '/sanguo3/', '--expected-build-id', f.build]
        command('不重新构建即可恢复完整同版本', restore)
        assert sha(root / 'restored/release-manifest.json') == sha(root / 'dist/release-manifest.json')
        command('恢复不能覆盖已有目录', restore, 1, 'already exists')
        bad_version = restore.copy()
        bad_version[bad_version.index('--output') + 1] = root / 'wrong-version-target'
        bad_version[-1] = 'wrong'
        command('错误回滚版本拒绝', bad_version, 1, 'buildId differs')
        (root / 'release.tar.gz.sha256').write_text('0' * 64 + '  release.tar.gz\n')
        command('归档传输损坏拒绝', restore, 1, 'SHA-256 mismatch')
        for kind in ['traversal', 'symlink', 'duplicate']:
            bad = root / (kind + '.tar.gz')
            with tarfile.open(bad, 'w:gz') as t:
                member = tarfile.TarInfo('../escape' if kind == 'traversal' else 'x')
                if kind == 'symlink':
                    member.type = tarfile.SYMTYPE; member.linkname = '/tmp/escape'; t.addfile(member)
                else:
                    member.size = 1; t.addfile(member, io.BytesIO(b'x'))
                    if kind == 'duplicate': t.addfile(member, io.BytesIO(b'y'))
            (root / (bad.name + '.sha256')).write_text(sha(bad) + '  ' + bad.name + '\n')
            command('恶意归档拒绝-' + kind, [TOOLS / 'release_archive.py', 'restore', '--archive', bad, '--checksum-file', root / (bad.name + '.sha256'), '--output', root / ('out-' + kind), '--expected-base', '/sanguo3/', '--expected-build-id', f.build], 1, 'unsafe or duplicate')
    print(json.dumps({'scope': 'Artificial fixtures for tools only; no game/original/site validated', 'total': len(RESULTS), 'passed': len(RESULTS), 'failed': 0, 'cases': RESULTS}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
