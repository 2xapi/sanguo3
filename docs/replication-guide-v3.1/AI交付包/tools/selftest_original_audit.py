#!/usr/bin/env python3
"""Exercise the byte-audit with the user's local sample and candidate data."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def run(cmd):
    return subprocess.run([sys.executable, str(Path(__file__).with_name('audit_original.py')), *map(str, cmd)], capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', required=True, type=Path)
    parser.add_argument('--candidate-dir', required=True, type=Path)
    args = parser.parse_args()
    results = []
    good = run(['--rom', args.rom, '--candidate-dir', args.candidate_dir])
    assert good.returncode == 0, good.stderr
    report = json.loads(good.stdout)
    assert report['candidateByteMismatches'] == 0 and report['battlefieldIndexConflict']['differingSlots'] == 99 and report['releaseReady'] is False
    results.append('所提供样本的已核对字段通过且报告99项战场冲突')
    with tempfile.TemporaryDirectory(prefix='original-audit-test-') as tmp:
        p = Path(tmp); (p/'wrong.bin').write_bytes(b'not the supplied sample')
        wrong = run(['--rom', p/'wrong.bin', '--candidate-dir', args.candidate_dir])
        assert wrong.returncode == 2 and 'does not match' in wrong.stderr
        results.append('拒绝错误样本摘要')
        shutil.copytree(args.candidate_dir, p/'data')
        target = p/'data/officers-532.json'
        data = json.loads(target.read_text()); data[0]['land'] ^= 1
        target.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        changed = run(['--rom', args.rom, '--candidate-dir', p/'data'])
        result = json.loads(changed.stdout)
        assert changed.returncode == 1 and result['candidateByteMismatches'] == 1 and result['byteMismatchExamples'][0]['item'] == '0:land'
        results.append('检出人工篡改的候选字段')
    print(json.dumps({'scope':'Read-only audit of supplied sample plus temporary negative test fixtures; no gameplay acceptance.', 'total':len(results), 'passed':len(results), 'failed':0, 'cases':results},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
