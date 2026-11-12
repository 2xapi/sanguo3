#!/usr/bin/env python3
"""Static template and embedded-script checks, never actual Actions execution."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
try:
    import yaml
except ImportError:
    yaml = None


def load_yaml(path):
    if yaml is not None:
        return yaml.load(path.read_text(), Loader=yaml.BaseLoader)
    # macOS ships Ruby/Psych; this is only a syntax-check fallback.
    p = subprocess.run(['ruby', '-ryaml', '-rjson', '-e', 'puts JSON.dump(YAML.load_file(ARGV[0]))', str(path)], capture_output=True, text=True)
    if p.returncode:
        raise ValueError(p.stderr)
    def strings(v):
        if isinstance(v, dict): return {str(k): strings(x) for k, x in v.items()}
        if isinstance(v, list): return [strings(x) for x in v]
        if isinstance(v, bool): return 'true' if v else 'false'
        return v
    return strings(json.loads(p.stdout))

KIT = Path(__file__).resolve().parent.parent


def main():
    results = []
    pins = {p['name']: p['commit'] for p in json.loads((KIT / 'templates/actions-pins.json').read_text())}
    workflows = {}
    for name in ['pages', 'rollback']:
        obj = load_yaml(KIT / ('templates/' + name + '.yml.example'))
        workflows[name] = obj
        assert obj['concurrency']['group'] == 'pages-production'
        for job_id, job in obj['jobs'].items():
            for i, step in enumerate(job['steps']):
                if 'uses' in step:
                    match = re.fullmatch(r'actions/([a-z-]+)@([a-f0-9]{40})', step['uses'])
                    assert match and pins[match[1]] == match[2], step['uses']
                    if match[1] == 'upload-pages-artifact': assert step['with']['include-hidden-files'] == 'true'
                if 'run' in step:
                    if step.get('shell') == 'python':
                        ast.parse(step['run'])
                    else:
                        p = subprocess.run(['/bin/bash', '-n'], input=step['run'], text=True, capture_output=True)
                        assert p.returncode == 0, p.stderr
        results.append({'case': name + ' YAML、锁定Actions与全部内嵌脚本语法', 'passed': True})
    jobs = workflows['pages']['jobs']
    assert jobs['transport-receive']['needs'] == 'transport-send'
    assert jobs['build']['needs'] == 'transport-receive' and jobs['deploy']['needs'] == 'build'
    results.append({'case': 'CI传递位于构建和完整门禁之前', 'passed': True})
    tasks = {t['id']: t for t in json.loads((KIT / 'templates/tasks.json').read_text())}
    assert tasks['OPS-PREP']['dependsOn'] == ['ENG-001']
    assert len(tasks) == 24
    results.append({'case': '24组任务无DIST到OPS-PREP的循环前置', 'passed': True})
    with tempfile.TemporaryDirectory(prefix='sanguo3-bootstrap-script-') as td:
        root = Path(td); out = root / 'out.txt'
        env = dict(os.environ, GITHUB_SHA='a' * 40, GITHUB_RUN_ID='1234', GITHUB_RUN_ATTEMPT='2', GITHUB_OUTPUT=str(out))
        sender = jobs['transport-send']['steps'][0]['run']
        receiver = next(s['run'] for s in jobs['transport-receive']['steps'] if s.get('shell') == 'python')
        import sys
        p = subprocess.run([sys.executable, '-c', sender], env=env, cwd=root, capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        digest = out.read_text().strip().split('=', 1)[1]
        env['EXPECTED_PAYLOAD_SHA'] = digest
        p = subprocess.run([sys.executable, '-c', receiver], env=env, cwd=root, capture_output=True, text=True)
        assert p.returncode == 0 and json.loads((root / 'bootstrap-transport.json').read_text())['passed'] is True
        (root / 'transport.json').write_text('changed between jobs')
        p = subprocess.run([sys.executable, '-c', receiver], env=env, cwd=root, capture_output=True, text=True)
        assert p.returncode != 0
    results.append({'case': '真实执行传递脚本能核对原字节并拒绝损坏', 'passed': True})
    deploy = jobs['deploy']['steps']
    assert any('exit 1' in s.get('run', '') and 'always()' in s.get('if', '') for s in deploy)
    assert any(s.get('with', {}).get('artifact_name') == 'rollback-pages' for s in deploy)
    assert any(s.get('env', {}).get('LIVE_LEDGER_MODE') == 'isolated' for s in deploy)
    results.append({'case': '恢复分支、独立报告与失败候选退出码存在', 'passed': True})
    assert not (KIT.parents[2] / '.github/workflows').exists()
    results.append({'case': '文档包未启用生产工作流', 'passed': True})
    print(json.dumps({'scope': 'YAML/script/static checks and local transport simulation only. Not GitHub execution.', 'total': len(results), 'passed': len(results), 'failed': 0, 'cases': results}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
