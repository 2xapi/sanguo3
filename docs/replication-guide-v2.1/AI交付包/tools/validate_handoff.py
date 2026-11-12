#!/usr/bin/env python3
"""Read-only ledger checker. Never substitutes for game tests or source evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

FILES = ['project', 'references', 'screens', 'features', 'reports', 'tasks', 'unknowns']
EVIDENCE = {'uncollected', 'collected', 'pending_verification', 'confirmed', 'conflict'}
COMPARE = {'not_run', 'failed', 'blocked', 'passed'}
IMPLEMENT = {'not_started', 'in_progress', 'implemented'}
TASK = {'todo', 'in_progress', 'verify', 'blocked', 'done'}
KINDS = {'original-screen', 'original-video', 'original-audio', 'original-rule-observation', 'original-data', 'original-manual'}
CATEGORIES = {'build', 'ui', 'dynamic', 'interaction', 'rules', 'data', 'ai', 'random', 'audio', 'save', 'compatibility', 'dist', 'live'}
FIDELITY = {'ui', 'dynamic', 'interaction', 'rules', 'data', 'ai', 'random', 'audio'}


def member(value, allowed):
    return isinstance(value, str) and value in allowed


def run(data_dir, artifact_root, mode):
    errors = []
    db = {}

    def check(ok, message):
        if not ok:
            errors.append(message)
        return bool(ok)

    for name in FILES:
        try:
            db[name] = json.loads((data_dir / (name + '.json')).read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as exc:
            errors.append(f'{name}.json: {exc}')
    if errors:
        return errors, db
    check(isinstance(db['project'], dict), 'project must be an object')
    for name in FILES[1:]:
        check(isinstance(db[name], list), f'{name} must be an array')
    if errors:
        return errors, db

    def records(name):
        result = {}
        for idx, row in enumerate(db[name]):
            if not check(isinstance(row, dict), f'{name}[{idx}] must be an object'):
                continue
            rid = row.get('id')
            if not check(isinstance(rid, str) and bool(rid.strip()), f'{name}[{idx}]: missing id'):
                continue
            check(rid not in result, f'{name}: duplicate id {rid}')
            result[rid] = row
        return result

    indexed = {name: records(name) for name in FILES[1:]}

    def links(row, field, target, label, required=False):
        values = row.get(field, [])
        if not check(isinstance(values, list), f'{label}.{field} must be an array'):
            return []
        valid = []
        for val in values:
            if check(isinstance(val, str) and val in target, f'{label}.{field}: missing linked id {val!r}'):
                valid.append(val)
        if required:
            check(bool(values), f'{label}.{field} must not be empty')
        return valid

    def local_file(raw, label, required=False):
        if not raw and not required:
            return None
        if not check(isinstance(raw, str) and bool(raw), f'{label}: local path required'):
            return None
        p = (artifact_root / raw).resolve()
        if not check(p.is_relative_to(artifact_root), f'{label}: path escapes artifact root'):
            return None
        try:
            if not check(p.is_file() and p.stat().st_size > 0, f'{label}: missing or empty artifact {raw}'):
                return None
        except OSError as exc:
            errors.append(f'{label}: {exc}')
            return None
        return p

    refs = indexed['references']
    reports = indexed['reports']
    tasks = indexed['tasks']
    unknowns = indexed['unknowns']
    strict = mode in {'exact-release', 'delivered'}
    candidate = db['project'].get('candidate', {})
    if not isinstance(candidate, dict):
        errors.append('project.candidate must be an object')
        candidate = {}
    if strict:
        check(isinstance(candidate.get('commit'), str) and bool(re.fullmatch('[a-f0-9]{40}', candidate['commit'])), 'candidate: full current source commit required')
        check(isinstance(candidate.get('buildId'), str) and bool(re.fullmatch('[A-Za-z0-9._-]+', candidate['buildId'])), 'candidate: current buildId required')
        base = candidate.get('basePath')
        check(isinstance(base, str) and bool(re.fullmatch(r'/(?:[A-Za-z0-9._-]+/)*', base)) and all(p not in {'.', '..'} for p in base.split('/')), 'candidate: normalized deployment basePath required')
    # Aggregating gates cannot require their own completion before they run.
    deferred = {'RELEASE-EXACT', 'OPS-LIVE', 'FINAL-DELIVERY'} if mode == 'exact-release' else {'FINAL-DELIVERY'}

    def original_links(ids, label):
        check(bool(ids), f'{label}: no original references')
        for rid in ids:
            ref = refs[rid]
            check(member(ref.get('kind'), KINDS) and ref.get('evidenceStatus') == 'confirmed', f'{label}: {rid} is not confirmed original evidence')

    for rid, ref in refs.items():
        check(isinstance(ref.get('kind'), str), f'{rid}: kind required')
        check(member(ref.get('evidenceStatus'), EVIDENCE), f'{rid}: invalid evidenceStatus')
        need_original = strict and member(ref.get('kind'), KINDS)
        path = local_file(ref.get('path'), f'{rid}.path', required=need_original)
        digest = ref.get('sha256')
        if digest is not None or need_original:
            if check(isinstance(digest, str) and bool(re.fullmatch('[0-9a-f]{64}', digest)), f'{rid}: valid sha256 required') and path:
                check(hashlib.sha256(path.read_bytes()).hexdigest() == digest, f'{rid}: sha256 mismatch')

    for name in ['screens', 'features']:
        for rid, row in indexed[name].items():
            check(member(row.get('evidenceStatus'), EVIDENCE), f'{rid}: invalid evidenceStatus')
            check(member(row.get('implementationStatus'), IMPLEMENT), f'{rid}: invalid implementationStatus')
            check(member(row.get('comparisonStatus'), COMPARE), f'{rid}: invalid comparisonStatus')
            refids = links(row, 'referenceIds', refs, rid, required=strict)
            reportids = links(row, 'reportIds', reports, rid, required=strict)
            cases = row.get('caseIds')
            check(isinstance(cases, list) and all(isinstance(c, str) and c for c in cases), f'{rid}: caseIds must be a string array')
            if strict:
                original_links(refids, rid)
                check(bool(cases), f'{rid}: no cases')
                check(row.get('evidenceStatus') == 'confirmed', f'{rid}: evidence not confirmed')
                check(row.get('implementationStatus') == 'implemented', f'{rid}: not implemented')
                check(row.get('comparisonStatus') == 'passed', f'{rid}: comparison not passed')
                if name == 'screens':
                    check(row.get('hasPlaceholder') is False, f'{rid}: placeholder state must explicitly be false')
                    check(row.get('pixelMode') == 'exact' and type(row.get('diffPixels')) is int and row['diffPixels'] == 0, f'{rid}: exact zero-pixel result required')
                    dyn = row.get('dynamicCoverageStatus')
                    check(member(dyn, {'passed', 'not_applicable'}), f'{rid}: dynamic coverage incomplete')
                    if dyn == 'not_applicable':
                        check(bool(row.get('dynamicNotApplicableReason')), f'{rid}: dynamic not-applicable needs reason')
                    if dyn == 'passed':
                        check(any(reports[x].get('category') == 'dynamic' for x in reportids), f'{rid}: dynamic report missing')
                    check(any(reports[x].get('category') == 'ui' for x in reportids), f'{rid}: ui report missing')
                else:
                    kind = row.get('kind')
                    check(member(kind, FIDELITY), f'{rid}: feature kind must map to a fidelity category')
                    check(any(reports[x].get('category') == kind for x in reportids), f'{rid}: category report missing')
                    if kind == 'random':
                        check(row.get('validationLevel') == 'sequence', f'{rid}: full sequence claim is not substantiated at ledger level')

    for rid, report in reports.items():
        check(member(report.get('category'), CATEGORIES), f'{rid}: invalid category')
        check(member(report.get('result'), {'passed', 'failed', 'blocked', 'not_run'}), f'{rid}: invalid result')
        for key in ['executed', 'failed', 'skipped']:
            value = report.get(key)
            check(type(value) is int and value >= 0, f'{rid}.{key}: nonnegative integer required')
        check(type(report.get('exitCode')) is int or report.get('exitCode') is None, f'{rid}: invalid exitCode')
        executed, failed = report.get('executed'), report.get('failed')
        if type(executed) is int and type(failed) is int:
            check(failed <= executed, f'{rid}: failed exceeds executed')
        paths = report.get('artifactPaths', [])
        if check(isinstance(paths, list), f'{rid}: artifactPaths must be an array'):
            for path in paths:
                local_file(path, f'{rid}.artifactPaths', required=True)
        else:
            paths = []
        refids = links(report, 'referenceIds', refs, rid)
        if strict:
            check(report.get('buildId') == candidate.get('buildId'), f'{rid}: stale or missing report buildId')
            check(report.get('commit') == candidate.get('commit'), f'{rid}: stale or missing report commit')
            check(report.get('result') == 'passed' and report.get('exitCode') == 0, f'{rid}: report did not pass')
            check(type(executed) is int and executed > 0, f'{rid}: zero or missing executed checks')
            check(report.get('failed') == 0 and report.get('skipped') == 0, f'{rid}: failed or skipped checks')
            check(bool(paths), f'{rid}: report has no actual artifacts')
            if member(report.get('category'), FIDELITY):
                original_links(refids, rid)
            if report.get('category') == 'live':
                expected = report.get('expectedBuildId')
                check(isinstance(expected, str) and bool(expected) and report.get('testedBuildId') == expected, f'{rid}: live build identity mismatch')
                from urllib.parse import urlsplit
                url = report.get('baseUrl')
                valid_url = isinstance(url, str) and urlsplit(url).scheme == 'https' and bool(urlsplit(url).netloc)
                check(valid_url, f'{rid}: live HTTPS baseUrl required')
                if valid_url:
                    check(urlsplit(url).path == candidate.get('basePath'), f'{rid}: live deployment base differs from candidate')
            if report.get('category') == 'ui':
                check(type(report.get('diffPixels')) is int and report['diffPixels'] == 0, f'{rid}: ui report has nonzero/unknown pixels')

    graph = {}
    for rid, task in tasks.items():
        check(member(task.get('status'), TASK), f'{rid}: invalid task status')
        graph[rid] = links(task, 'dependsOn', tasks, rid)
        links(task, 'blockerIds', unknowns, rid)
        reportids = links(task, 'reportIds', reports, rid)
        acceptance = task.get('acceptance')
        check(isinstance(acceptance, list) and bool(acceptance) and all(isinstance(x, str) and x for x in acceptance), f'{rid}: acceptance must be a nonempty string array')
        paths = task.get('outputPaths', [])
        if check(isinstance(paths, list), f'{rid}: outputPaths must be an array'):
            for path in paths:
                local_file(path, f'{rid}.outputPaths', required=True)
        else:
            paths = []
        if task.get('status') == 'done':
            check(bool(reportids) and bool(paths), f'{rid}: done task needs report and output')
            for dep in graph[rid]:
                check(tasks[dep].get('status') == 'done', f'{rid}: dependency {dep} not done')
            for reportid in reportids:
                check(reports[reportid].get('result') == 'passed', f'{rid}: completion report not passed')
        if strict and task.get('required', True) and rid not in deferred:
            check(task.get('status') == 'done', f'{rid}: required task not done')

    visited, active = set(), set()

    def visit(node):
        if node in active:
            errors.append(f'tasks: dependency cycle at {node}')
            return
        if node in visited:
            return
        active.add(node)
        for dep in graph.get(node, []):
            visit(dep)
        active.remove(node)
        visited.add(node)

    for rid in graph:
        visit(rid)

    for rid, unknown in unknowns.items():
        check(member(unknown.get('status'), {'open', 'resolved'}), f'{rid}: invalid unknown status')
        refids = links(unknown, 'referenceIds', refs, rid)
        if unknown.get('status') == 'resolved':
            check(bool(unknown.get('resolution')) and bool(refids), f'{rid}: resolution and references required')
        if strict:
            check(unknown.get('status') == 'resolved', f'{rid}: unresolved original uncertainty')

    project = db['project']
    check(project.get('schemaVersion') == 1, 'project: schemaVersion must be 1')
    for key in ['target', 'display', 'inventory', 'strictTarget']:
        check(isinstance(project.get(key), dict), f'project.{key}: object required')
    required = project.get('requiredCoverage')
    if check(isinstance(required, list) and all(isinstance(x, str) for x in required), 'project.requiredCoverage: string array required'):
        check(set(required) == CATEGORIES, 'project.requiredCoverage: strict coverage categories must not be removed')
    if strict:
        display = project.get('display', {})
        inventory = project.get('inventory', {})
        target = project.get('target', {})
        strict_target = project.get('strictTarget', {})
        if isinstance(target, dict):
            check(target.get('identityStatus') == 'confirmed', 'project: target identity unconfirmed')
            check(target.get('language') == 'zh-Hant', 'project: target language changed')
        if isinstance(display, dict):
            for key in ['logicalWidth', 'logicalHeight']:
                check(type(display.get(key)) is int and display[key] > 0, f'project.display.{key}: unconfirmed')
            check(bool(display.get('primaryMode')), 'project: display mode unconfirmed')
            original_links(links(display, 'referenceIds', refs, 'display', required=True), 'display')
        if isinstance(inventory, dict):
            check(inventory.get('status') == 'confirmed', 'project: inventory completeness not confirmed')
            original_links(links(inventory, 'referenceIds', refs, 'inventory', required=True), 'inventory')
        if isinstance(strict_target, dict):
            check(strict_target.get('placeholderAllowed') is False and strict_target.get('pixelDifferenceAllowed') == 0 and strict_target.get('unknownAllowed') is False, 'project: strict target weakened')
        check(bool(indexed['screens']), 'screens: empty inventory cannot substantiate a complete game')
        check(bool(indexed['features']), 'features: empty inventory cannot substantiate a complete game')
        check(bool(tasks), 'tasks: required work cannot be an empty ledger')
        for gate_id in ['RELEASE-EXACT', 'OPS-LIVE', 'FINAL-DELIVERY']:
            check(gate_id in tasks, f'tasks: mandatory gate missing {gate_id}')
        passed_categories = {r.get('category') for r in reports.values() if r.get('result') == 'passed' and isinstance(r.get('category'), str)}
        expected_categories = CATEGORIES - {'live'} if mode == 'exact-release' else CATEGORIES
        for category in sorted(expected_categories - passed_categories):
            errors.append(f'reports: missing passed category {category}')
    return errors, db


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('templates'))
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--mode', choices=['structure', 'exact-release', 'delivered'], default='structure')
    args = parser.parse_args()
    data_dir = args.data.resolve()
    root = (args.artifact_root or data_dir.parent).resolve()
    errors, db = run(data_dir, root, args.mode)
    print(f'MODE: {args.mode}')
    for name in FILES[1:]:
        print(f'{name}: {len(db.get(name, [])) if isinstance(db.get(name), list) else "invalid"}')
    for err in errors:
        print('BLOCK:', err)
    print('RESULT:', 'BLOCKED' if errors else 'PASS')
    print('This checks ledger consistency only; it does not prove original-game equivalence.')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
