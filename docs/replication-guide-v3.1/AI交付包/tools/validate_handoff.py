#!/usr/bin/env python3
"""Compare frozen scope with executed case artifacts; does not certify provenance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from verify_dist import validate as validate_dist

FILES = ['project', 'scope', 'references', 'screens', 'features', 'cases', 'reports', 'tasks', 'unknowns']
CATEGORIES = {'bootstrap', 'build', 'ui', 'dynamic', 'interaction', 'rules', 'data', 'ai', 'random', 'audio', 'save', 'compatibility', 'dist', 'live'}
FIDELITY = {'ui', 'dynamic', 'interaction', 'rules', 'data', 'ai', 'random', 'audio'}
GATES = {'RELEASE-EXACT': 'release_gate', 'OPS-LIVE': 'post_deploy', 'FINAL-DELIVERY': 'final_gate'}
ORIGINAL_KINDS = {'original-screen', 'original-video', 'original-audio', 'original-rule-observation', 'original-data', 'original-manual'}
HASH = re.compile(r'[a-f0-9]{64}')
COMMIT = re.compile(r'[a-f0-9]{40}')
BUILD = re.compile(r'[A-Za-z0-9._-]+')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def site(value):
    if not isinstance(value, str):
        return None
    try:
        u = urlsplit(value)
        if (u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment
                or not re.fullmatch(r'/(?:[A-Za-z0-9._-]+/)*', u.path)
                or any(p in {'.', '..'} for p in u.path.split('/'))):
            return None
        return u.hostname.lower(), u.port or 443, u.path
    except ValueError:
        return None


def pointer(value, path):
    """Read a JSON value using RFC 6901 without interpreting it as code."""
    if path == '':
        return value
    if not isinstance(path, str) or not path.startswith('/'):
        raise ValueError('JSON pointer must be empty or start with /')
    for part in path[1:].split('/'):
        if re.search(r'~(?![01])', part):
            raise ValueError('invalid JSON pointer escape')
        key = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', key):
                raise ValueError('invalid array index')
            value = value[int(key)]
        elif isinstance(value, dict):
            value = value[key]
        else:
            raise ValueError('pointer traverses a scalar')
    return value


def run(data_dir, root, mode, scope_sha=None, expected_commit=None, expected_build=None):
    errors, db = [], {}
    strict = mode != 'structure'

    def check(ok, message):
        if not ok:
            errors.append(message)
        return bool(ok)

    def read(path, label):
        def unique(pairs):
            result = {}
            for k, v in pairs:
                if k in result:
                    raise ValueError('duplicate JSON key: ' + k)
                result[k] = v
            return result
        try:
            return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=unique,
                              parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        except (OSError, UnicodeError, ValueError, RecursionError) as exc:
            errors.append(f'{label}: unreadable JSON: {exc}')
            return None

    def local(value, label):
        if not check(isinstance(value, str) and bool(value), label + ': path required'):
            return None
        p = (root / value).resolve()
        if check(p.is_relative_to(root) and p.is_file() and p.stat().st_size > 0, label + ': missing, empty or outside artifact root'):
            return p
        return None

    def strings(value, label, required=False):
        ok = isinstance(value, list) and all(isinstance(v, str) and bool(v) for v in value)
        if ok:
            ok = len(value) == len(set(value)) and (bool(value) or not required)
        return check(ok, label + ': unique string array required')

    for name in FILES:
        db[name] = read(data_dir / (name + '.json'), name)
    if errors:
        return errors, db
    for name in ['project', 'scope']:
        check(isinstance(db[name], dict), name + ': object required')
    for name in FILES[2:]:
        check(isinstance(db[name], list), name + ': array required')
    if errors:
        return errors, db
    ix = {}
    for name in FILES[2:]:
        ix[name] = {}
        for row in db[name]:
            if not check(isinstance(row, dict) and isinstance(row.get('id'), str) and bool(row['id']), name + ': record id required'):
                continue
            check(row['id'] not in ix[name], name + ': duplicate id ' + row['id'])
            ix[name][row['id']] = row
    p, s = db['project'], db['scope']
    check(type(p.get('schemaVersion')) is int and p['schemaVersion'] == 2, 'project: schemaVersion must be 2')
    check(type(s.get('schemaVersion')) is int and s['schemaVersion'] == 1, 'scope: schemaVersion must be 1')
    for key in ['target', 'display', 'inventory', 'strictTarget', 'candidate']:
        check(isinstance(p.get(key), dict), 'project.' + key + ': object required')
    for key in ['target', 'display', 'inventory', 'strictTarget', 'deployment', 'references', 'screens', 'features', 'cases', 'tasks']:
        check(isinstance(s.get(key), dict), 'scope.' + key + ': object required')
    strings(p.get('requiredCoverage'), 'project.requiredCoverage')
    strings(s.get('requiredCoverage'), 'scope.requiredCoverage')
    if errors:
        return errors, db

    def links(row, field, target, label, required=False):
        values = row.get(field, [])
        if not strings(values, label + '.' + field, required):
            return []
        for value in values:
            check(value in target, label + ': missing linked ' + field + ' ' + value)
        return [v for v in values if v in target]

    for name in ['screens', 'features', 'cases']:
        for ident, row in ix[name].items():
            links(row, 'referenceIds', ix['references'], ident)
            links(row, 'reportIds', ix['reports'], ident)
            if name != 'cases':
                links(row, 'caseIds', ix['cases'], ident)
    graph = {}
    for ident, task in ix['tasks'].items():
        check(task.get('status') in ['todo', 'in_progress', 'verify', 'blocked', 'done'], ident + ': invalid task status')
        check(type(task.get('required')) is bool, ident + ': required boolean missing')
        graph[ident] = links(task, 'dependsOn', ix['tasks'], ident)
        links(task, 'caseIds', ix['cases'], ident)
        links(task, 'reportIds', ix['reports'], ident)
        links(task, 'blockerIds', ix['unknowns'], ident)
        strings(task.get('acceptance'), ident + '.acceptance', True)
        strings(task.get('outputPaths', []), ident + '.outputPaths')
        if task.get('status') == 'done':
            for dep in graph[ident]:
                check(ix['tasks'][dep].get('status') == 'done', ident + ': dependency not done ' + dep)
    active, visited = set(), set()

    def visit(ident):
        if ident in active:
            errors.append('task dependency cycle: ' + ident)
            return
        if ident in visited:
            return
        active.add(ident)
        for dep in graph[ident]:
            visit(dep)
        active.remove(ident)
        visited.add(ident)

    for ident in graph:
        visit(ident)
    for ident, unknown in ix['unknowns'].items():
        check(unknown.get('status') in ['open', 'resolved'], ident + ': invalid unknown status')
        refs = links(unknown, 'referenceIds', ix['references'], ident)
        if unknown.get('status') == 'resolved':
            check(bool(unknown.get('resolution')) and bool(refs), ident + ': resolution evidence required')
    if errors or not strict:
        return errors, db

    candidate = p['candidate']
    check(s.get('status') == 'frozen', 'scope not frozen; original specifications incomplete')
    check(isinstance(scope_sha, str) and bool(HASH.fullmatch(scope_sha)), 'trusted scope SHA required outside mutable ledger')
    check(sha(data_dir / 'scope.json') == scope_sha, 'scope differs from trusted anchor')
    check(isinstance(expected_commit, str) and bool(COMMIT.fullmatch(expected_commit)), 'external expected commit required')
    check(isinstance(expected_build, str) and bool(BUILD.fullmatch(expected_build)), 'external expected buildId required')
    check(candidate.get('commit') == expected_commit, 'candidate differs from external commit')
    check(candidate.get('buildId') == expected_build, 'candidate differs from external buildId')
    check(bool(s.get('baselineId')) and s.get('baselineId') == p['target'].get('baselineId'), 'baseline mismatch')
    for key in ['target', 'display', 'inventory', 'strictTarget', 'requiredCoverage']:
        check(p[key] == s[key], key + ': differs from frozen scope')
    target = s['target']
    check(target.get('identityStatus') == 'confirmed' and target.get('language') == 'zh'
          and target.get('observedScript') == 'mixed'
          and target.get('scriptPolicy') == 'preserve-original-mixed-glyphs', 'target identity/language or glyph policy unconfirmed')
    target_sha = target.get('binarySha256')
    check(isinstance(target_sha, str) and bool(HASH.fullmatch(target_sha)), 'target binary SHA-256 required')
    check(any(ix['references'].get(r, {}).get('kind') == 'original-data'
              and ix['references'].get(r, {}).get('sha256') == target_sha
              for r in target.get('referenceIds', [])), 'target digest must link to an original-data reference')
    for key in ['logicalWidth', 'logicalHeight']:
        check(type(s['display'].get(key)) is int and s['display'][key] > 0, 'unconfirmed display ' + key)
    check(bool(s['display'].get('primaryMode')), 'display mode unconfirmed')
    check(s['inventory'].get('status') == 'confirmed', 'complete original inventory unconfirmed')
    check(s['strictTarget'] == {'placeholderAllowed': False, 'pixelDifferenceAllowed': 0, 'unknownAllowed': False}, 'strict target weakened')
    check(set(s['requiredCoverage']) == CATEGORIES, 'frozen coverage categories incomplete')
    expected_url = s['deployment'].get('baseUrl')
    expected_site = site(expected_url)
    check(expected_site is not None, 'frozen production HTTPS origin required')
    check(site(candidate.get('baseUrl')) == expected_site and expected_site is not None, 'candidate production origin/path mismatch')
    check(expected_site is not None and candidate.get('basePath') == expected_site[2] == s['deployment'].get('basePath'), 'candidate basePath mismatch')
    manifest = local(candidate.get('manifestPath'), 'candidate manifest')
    if manifest:
        check(manifest.name == 'release-manifest.json', 'candidate manifest filename mismatch')
        dist_errors, built = validate_dist(manifest.parent, candidate.get('basePath'), True)
        errors.extend('dist: ' + e for e in dist_errors)
        for key in ['commit', 'buildId', 'basePath']:
            check(built.get(key) == candidate.get(key), 'runtime manifest differs from candidate ' + key)
    for name in ['references', 'screens', 'features', 'cases', 'tasks']:
        check(bool(s[name]), 'empty frozen ' + name + ' inventory')
        check(set(s[name]) == set(ix[name]), name + ': inventory differs from frozen scope')
        check(all(isinstance(v, dict) for v in s[name].values()), name + ': frozen policies must be objects')
    if errors:
        return errors, db

    for ident, ref in ix['references'].items():
        policy = s['references'][ident]
        check(ref.get('kind') in ORIGINAL_KINDS and ref.get('evidenceStatus') == 'confirmed', ident + ': original reference unconfirmed')
        for key in ['path', 'sha256', 'kind']:
            check(ref.get(key) == policy.get(key), ident + ': frozen reference changed ' + key)
        path = local(ref.get('path'), ident)
        if path:
            check(sha(path) == policy.get('sha256'), ident + ': original digest mismatch')
    for group in ['target', 'display', 'inventory']:
        links(s[group], 'referenceIds', ix['references'], group, True)
    for ident, unknown in ix['unknowns'].items():
        check(unknown.get('status') == 'resolved', ident + ': unresolved original fact')
    specs, category_cases, assertions = {}, {c: set() for c in CATEGORIES}, {}
    for ident, policy in s['cases'].items():
        case = ix['cases'][ident]
        category = policy.get('category')
        if not check(isinstance(category, str) and category in CATEGORIES, ident + ': invalid category'):
            continue
        category_cases[category].add(ident)
        for key in ['category', 'specificationPath', 'specificationSha256']:
            check(case.get(key) == policy.get(key), ident + ': frozen case changed ' + key)
        path = local(case.get('specificationPath'), ident + ' spec')
        if not path:
            continue
        check(sha(path) == policy.get('specificationSha256'), ident + ': specification digest mismatch')
        spec = read(path, ident + ' spec')
        if not check(isinstance(spec, dict), ident + ': specification object required'):
            continue
        check(spec.get('caseId') == ident and spec.get('category') == category, ident + ': spec identity mismatch')
        refs = links(spec, 'referenceIds', ix['references'], ident + ' spec', category in FIDELITY)
        check(set(case.get('referenceIds', [])) == set(refs), ident + ': case/spec reference mismatch')
        rows = spec.get('assertions')
        if not check(isinstance(rows, list) and bool(rows) and all(isinstance(a, dict) for a in rows), ident + ': assertions required'):
            continue
        ids = [a.get('id') for a in rows]
        if not strings(ids, ident + '.assertionIds', True):
            continue
        for a in rows:
            check(a.get('op') in ['equals', 'state_equal', 'sequence_equal', 'hash_equal', 'url_equal', 'pixel_equal'], ident + ': invalid operation')
            if a.get('op') == 'pixel_equal':
                check(any(ix['references'][r].get('path') == a.get('referencePath') and ix['references'][r].get('sha256') == a.get('referenceSha256') and ix['references'][r].get('kind') == 'original-screen' and ix['references'][r].get('captureQuality') == 'native-unscaled' and s['references'][r].get('captureQuality') == 'native-unscaled' for r in refs), ident + ': pixel reference must be a frozen native-unscaled original screen')
            else:
                check(('expected' in a) ^ ('expectedFrom' in a), ident + ': exactly one expected source required')
                if 'expectedFrom' in a:
                    check(a['expectedFrom'] in ['candidate.commit', 'candidate.buildId', 'deployment.baseUrl'], ident + ': unsupported expectedFrom')
        if category == 'ui':
            check(any(a.get('op') == 'pixel_equal' for a in rows), ident + ': UI requires actual pixel comparison')
        if category == 'live':
            check({'candidate.commit', 'candidate.buildId', 'deployment.baseUrl'}.issubset({a.get('expectedFrom') for a in rows}), ident + ': live assertions must bind commit, buildId and URL')
        assertions[ident], specs[ident] = set(ids), spec
    for category, ids in category_cases.items():
        check(bool(ids), 'no frozen cases for ' + category)
    if errors:
        return errors, db

    results, case_report = {}, {}
    for ident, entry in ix['reports'].items():
        path = local(entry.get('path'), ident + ' report')
        if not path:
            continue
        check(sha(path) == entry.get('sha256'), ident + ': report digest mismatch')
        raw = read(path, ident)
        if not check(isinstance(raw, dict), ident + ': report object required'):
            continue
        check(raw.get('reportId') == ident, ident + ': report identity mismatch')
        for key in ['buildId', 'commit']:
            check(raw.get(key) == candidate.get(key), ident + ': stale report ' + key)
        check(type(raw.get('exitCode')) is int and raw['exitCode'] == 0, ident + ': runner failed')
        check(isinstance(raw.get('command'), list) and bool(raw['command']) and all(isinstance(x, str) and x for x in raw['command']), ident + ': actual command required')
        check(isinstance(raw.get('runner'), str) and bool(raw['runner']), ident + ': runner required')
        artifacts = {}
        ars = raw.get('artifacts')
        if not check(isinstance(ars, list) and bool(ars), ident + ': hashed artifacts required'):
            continue
        for ar in ars:
            if not check(isinstance(ar, dict), ident + ': invalid artifact'):
                continue
            ap = local(ar.get('path'), ident + ' artifact')
            if ap:
                check(ar['path'] not in artifacts, ident + ': duplicate artifact')
                check(sha(ap) == ar.get('sha256'), ident + ': artifact digest mismatch')
                artifacts[ar['path']] = ap
        rows = raw.get('results')
        if not check(isinstance(rows, list) and bool(rows), ident + ': zero executed cases'):
            continue
        for row in rows:
            if not check(isinstance(row, dict), ident + ': invalid result'):
                continue
            cid = row.get('caseId')
            if not check(isinstance(cid, str) and cid in specs, ident + ': unregistered executed case ' + str(cid)):
                continue
            check(cid not in results, cid + ': duplicate selected execution')
            results[cid], case_report[cid] = row, ident
            check(row.get('status') == 'passed', cid + ': failed, skipped or unrun')
            actuals = row.get('assertions')
            if not check(isinstance(actuals, list) and all(isinstance(a, dict) and isinstance(a.get('id'), str) for a in actuals), cid + ': assertion results required'):
                continue
            got = {a['id']: a for a in actuals}
            check(len(got) == len(actuals) and set(got) == assertions[cid], cid + ': assertion results incomplete or duplicated')
            for a in specs[cid]['assertions']:
                result = got.get(a['id'], {})
                check(result.get('status') == 'passed', cid + ': assertion did not pass ' + a['id'])
                if a['op'] == 'pixel_equal':
                    rp, ap = local(a.get('referencePath'), cid + ' original PNG'), artifacts.get(result.get('actualPath'))
                    check(ap is not None, cid + ': captured PNG missing from hashed artifacts')
                    if rp and ap:
                        try:
                            from PIL import Image
                            check(not rp.samefile(ap), cid + ': reference cannot be compared with itself')
                            with Image.open(rp) as x, Image.open(ap) as y:
                                check(x.format == y.format == 'PNG', cid + ': exact images must be PNG')
                                check(all(im.mode in {'1', 'L', 'LA', 'P', 'RGB', 'RGBA'} and getattr(im, 'n_frames', 1) == 1 for im in [x, y]), cid + ': unsupported image mode or animation')
                                check(all(path.read_bytes()[24] in {1, 2, 4, 8} for path in [rp, ap]), cid + ': unsupported PNG bit depth')
                                check(x.size == y.size == (s['display']['logicalWidth'], s['display']['logicalHeight']), cid + ': image size mismatch')
                                check(x.convert('RGBA').tobytes() == y.convert('RGBA').tobytes(), cid + ': captured pixels differ')
                                check(all(x.info.get(k) == y.info.get(k) for k in ['icc_profile', 'gamma', 'srgb', 'chromaticity']), cid + ': color metadata differ')
                        except (ImportError, OSError, ValueError) as exc:
                            errors.append(cid + ': pixel verification failed: ' + str(exc))
                    continue
                source = result.get('actualFrom', {})
                if not check(isinstance(source, dict), cid + ': actualFrom required'):
                    continue
                ap = artifacts.get(source.get('path'))
                if not check(ap is not None, cid + ': actual source missing from hashed artifacts'):
                    continue
                observed = read(ap, cid + ' observation')
                try:
                    actual = pointer(observed, source.get('pointer'))
                    expected = a.get('expected') if 'expected' in a else {'candidate.commit': candidate['commit'], 'candidate.buildId': candidate['buildId'], 'deployment.baseUrl': expected_url}[a['expectedFrom']]
                    if a['op'] == 'url_equal':
                        check(site(actual) is not None and site(actual) == site(expected), cid + ': URL differs from frozen expected')
                    else:
                        check(canonical(actual) == canonical(expected), cid + ': actual differs from frozen expected ' + a['id'])
                    if a['op'] == 'hash_equal':
                        check(isinstance(actual, str) and bool(HASH.fullmatch(actual)), cid + ': invalid observed hash')
                except (KeyError, IndexError, TypeError, ValueError) as exc:
                    errors.append(cid + ': cannot evaluate assertion ' + a['id'] + ': ' + str(exc))
            if s['cases'][cid]['category'] == 'live':
                check(raw.get('expectedBuildId') == raw.get('testedBuildId') == candidate['buildId'], ident + ': live build identity mismatch')
                check(site(raw.get('baseUrl')) == expected_site, ident + ': wrong production origin or path')

    required_cases = set(specs) - (category_cases['live'] if mode == 'exact-release' else set())
    check(required_cases.issubset(results), 'missing selected case executions: ' + ','.join(sorted(required_cases - results.keys())))
    for ident, case in ix['cases'].items():
        if ident in required_cases:
            check(case_report.get(ident) in case.get('reportIds', []), ident + ': execution not linked to case')
    for name in ['screens', 'features']:
        for ident, policy in s[name].items():
            row = ix[name][ident]
            check(row.get('evidenceStatus') == 'confirmed' and row.get('implementationStatus') == 'implemented' and row.get('comparisonStatus') == 'passed', ident + ': implementation/comparison incomplete')
            for key in ['caseIds', 'referenceIds']:
                check(row.get(key) == policy.get(key) and bool(row.get(key)), ident + ': frozen ' + key + ' mismatch')
            cats = set()
            for cid in row.get('caseIds', []):
                if check(cid in specs, ident + ': unregistered linked case ' + cid):
                    cats.add(s['cases'][cid]['category'])
                    check(case_report.get(cid) in row.get('reportIds', []), ident + ': linked report did not execute case ' + cid)
            if name == 'screens':
                check(row.get('hasPlaceholder') is False and {'ui', 'dynamic', 'interaction'}.issubset(cats), ident + ': screen coverage incomplete or placeholder')
            else:
                check(row.get('kind') in FIDELITY, ident + ': feature must belong to a fidelity category')
                check(row.get('kind') == policy.get('kind') and row.get('kind') in cats, ident + ': feature category coverage mismatch')
                if row.get('kind') == 'random':
                    check(row.get('validationLevel') == 'sequence', ident + ': original random sequence unproven')
    for ident, policy in s['tasks'].items():
        task, phase = ix['tasks'][ident], policy.get('phase')
        check(phase == GATES[ident] if ident in GATES else phase in ['bootstrap', 'implementation'], ident + ': invalid frozen phase')
        for key in ['phase', 'required', 'dependsOn', 'acceptance', 'caseIds']:
            check(task.get(key) == policy.get(key), ident + ': frozen task changed ' + key)
        deferred = ['release_gate', 'post_deploy', 'final_gate'] if mode == 'exact-release' else ['final_gate']
        needed = phase not in deferred
        if needed and policy.get('required'):
            check(task.get('status') == 'done', ident + ': required task not done')
        if task.get('status') == 'done':
            check(bool(task.get('outputPaths')), ident + ': completed task needs output')
            for value in task.get('outputPaths', []):
                local(value, ident + ' output')
            if ident in ['RELEASE-EXACT', 'FINAL-DELIVERY']:
                if needed:
                    receipts = [read(root / value, ident + ' gate receipt') for value in task.get('outputPaths', []) if value.endswith('.json')]
                    check(any(isinstance(r, dict) and r.get('result') == 'passed' and r.get('mode') == 'exact-release' and r.get('scopeSha256') == scope_sha and r.get('commit') == candidate['commit'] and r.get('buildId') == candidate['buildId'] for r in receipts), ident + ': current release gate receipt required')
            else:
                check(bool(task.get('caseIds')), ident + ': task has no frozen cases')
                for cid in task.get('caseIds', []):
                    check(case_report.get(cid) in task.get('reportIds', []), ident + ': task case has no linked execution ' + cid)
    for ident, phase in GATES.items():
        check(ident in s['tasks'] and s['tasks'][ident].get('phase') == phase and s['tasks'][ident].get('required') is True, 'mandatory gate missing or optional: ' + ident)
    return errors, db


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('reference/ledgers'))
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--mode', choices=['structure', 'exact-release', 'delivered'], default='structure')
    parser.add_argument('--scope-sha256', default=os.environ.get('TRUSTED_SCOPE_SHA256'))
    parser.add_argument('--expected-commit', default=os.environ.get('EXPECTED_CANDIDATE_COMMIT'))
    parser.add_argument('--expected-build-id', default=os.environ.get('EXPECTED_CANDIDATE_BUILD_ID'))
    parser.add_argument('--write-report', type=Path)
    args = parser.parse_args()
    data_dir = args.data.resolve()
    root = (args.artifact_root or data_dir.parent).resolve()
    try:
        errors, db = run(data_dir, root, args.mode, args.scope_sha256, args.expected_commit, args.expected_build_id)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        errors, db = ['malformed evidence: ' + str(exc)], {}
    candidate = db.get('project', {}).get('candidate', {}) if isinstance(db.get('project'), dict) else {}
    receipt = {'result': 'blocked' if errors else 'passed', 'mode': args.mode, 'scopeSha256': args.scope_sha256,
               'commit': candidate.get('commit'), 'buildId': candidate.get('buildId'), 'errors': errors,
               'scope': 'Registered artifacts only; original provenance, inventory completeness and runner honesty require independent review.'}
    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    print('RESULT:', 'BLOCKED' if errors else 'PASS')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
