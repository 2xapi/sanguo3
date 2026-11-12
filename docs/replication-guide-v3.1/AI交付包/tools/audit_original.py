#!/usr/bin/env python3
"""Read-only byte comparison of the supplied baseline with candidate JSON.

This does not establish that field names or inferred rules are correct, and it
never exports the game binary or graphics. It explicitly flags the battlefield
indexing conflict and therefore cannot certify a release.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

TARGET = 'bd1bf6e238c9517244f9fd4bb15bf1baca5c0e0560614ccbb7234f43f5010960'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(rom_path, data):
    b = rom_path.read_bytes()
    actual = hashlib.sha256(b).hexdigest()
    if actual != TARGET:
        raise ValueError('ROM SHA-256 does not match the user-supplied baseline: ' + actual)
    if len(b) != 0x180000 or b[0x100:0x110] != b'SEGA MEGA DRIVE ':
        raise ValueError('unexpected baseline length or header')
    w = lambda off: int.from_bytes(b[off:off + 2], 'big')
    l = lambda off: int.from_bytes(b[off:off + 4], 'big')
    def load(name):
        return json.loads((data / name).read_text(encoding='utf-8'))
    errors, counts = [], {}
    def eq(group, label, observed, expected):
        counts[group] = counts.get(group, 0) + 1
        if observed != expected:
            errors.append({'group': group, 'item': label, 'candidate': observed, 'binary': expected})
    officers, coords, cities, fields = [load(n) for n in ['officers-532.json', 'city-coords.json', 'cities-46.json', 'battlefields-22.json']]
    if [len(officers), len(coords), len(cities), len(fields)] != [532, 46, 46, 22]:
        raise ValueError('candidate array lengths differ from the audited tables')
    names = ['land', 'water', 'war', 'int', 'pol', 'cha', 'xiang', 'yi', 'clan', 'birth']
    for i, obj in enumerate(officers):
        r = 0x78e95 + i * 30
        eq('officer_ids', str(i), obj['id'], i)
        for j, name in enumerate(names):
            eq('officer_candidate_values', f'{i}:{name}', obj[name], b[r + 4 + j])
        glyphs = []
        for j in range(14, 30, 2):
            code = w(r + j)
            if code < 0x8140:
                break
            glyphs.append(f'{code:04X}')
        eq('officer_glyph_codes', str(i), obj.get('nameGlyphs', '').upper(), ' '.join(glyphs))
    for i in range(46):
        r = 0x7ef6c + i * 26
        for name, val in [('id', i), ('x', b[r + 1]), ('y', w(r + 2)), ('f4', w(r + 4)), ('f6', w(r + 6))]:
            eq('city_coord_candidates', f'{i}:{name}', coords[i][name], val)
        for name, val in [('id', i), ('x', w(r + 4)), ('y', w(r + 6))]:
            eq('city_second_coord_candidates', f'{i}:{name}', cities[i][name], val)
    pointers = [l(0x8c620 + i * 4) for i in range(18)]
    conflicts = []
    for sc in range(6):
        obj = load(f'scenarios/scenario-{sc}.json')
        deploy, city, force = pointers[sc], pointers[6 + sc], pointers[12 + sc]
        for name, val in [('deploy', deploy), ('city', city), ('force', force)]:
            eq('scenario_pointers', f'{sc}:{name}', int(obj['blocks'][name], 16), val)
        eq('scenario_metadata', f'{sc}:raw', bytes.fromhex(obj['metaRaw']).hex(), b[0x81bb6 + sc*34:0x81bb6 + (sc+1)*34].hex())
        if [len(obj[k]) for k in ('cities', 'officers', 'forces', 'battlefields')] != [46, 531, 21, 22]:
            raise ValueError(f'scenario {sc} candidate table length mismatch')
        for i, row in enumerate(obj['cities']):
            eq('scenario_city_raw_records', f'{sc}:{i}', bytes.fromhex(row['raw']).hex(), b[city + i*32:city + (i+1)*32].hex())
        for i, row in enumerate(obj['officers']):
            r = deploy + i*4
            for k, val in [('id', i), ('troopsRaw', b[r]*100), ('status', b[r+1]), ('unk2', b[r+2]), ('city', b[r+3] if b[r+3] < 46 else None)]:
                eq('scenario_deployment_values', f'{sc}:{i}:{k}', row[k], val)
        for i, row in enumerate(obj['forces']):
            r = force + i*26; lord = w(r)
            for k, val in [('index', i), ('lordId', lord), ('active', lord != 0xffff), ('relations', list(b[r+4:r+25])), ('pad', b[r+25])]:
                eq('scenario_force_values', f'{sc}:{i}:{k}', row[k], val)
            if lord != 0xffff:
                eq('scenario_force_values', f'{sc}:{i}:capital', row['capital'], b[r+2])
        for i, row in enumerate(obj['battlefields']):
            legacy = b[0x800e4 + sc*22 + i]
            code = b[0x800e4 + i*6 + sc]
            eq('battlefield_candidate_old_stride', f'{sc}:{i}', row['state'], legacy)
            eq('battlefield_per_scenario_old_stride', f'{sc}:{i}', fields[i]['perScenario'][sc], legacy)
            if legacy != code:
                conflicts.append({'scenarioIndex': sc, 'battlefieldIndex': i, 'candidateOldStride': legacy, 'decompiledCodeStride': code})
    checksum = sum(w(i) for i in range(0x200, len(b), 2)) & 0xffff
    eq('header_checksum', 'checksum', w(0x18e), checksum)
    raw_xuchang = w(pointers[8] + 18*32 + 8)
    return {'baseline': {'sha256': actual, 'bytes': len(b), 'format': 'flat big-endian MD BIN', 'headerChecksum': f'{w(0x18e):04x}', 'resetVector': f'0x{l(4):x}'},
            'candidateFiles': {name: digest(data/name) for name in ['officers-532.json','city-coords.json','cities-46.json','battlefields-22.json'] + [f'scenarios/scenario-{i}.json' for i in range(6)]},
            'counts': counts, 'candidateByteMismatches': len(errors), 'byteMismatchExamples': errors[:20],
            'battlefieldIndexConflict': {'slotsCompared': 132, 'differingSlots': len(conflicts), 'examples': conflicts[:10], 'candidateFormula': '0x800e4 + scenario*22 + battlefield', 'decompiledFormula': '0x800e4 + battlefield*6 + scenario', 'source': 'docs/rea-ghidra/full-decomp/f_0001bbd2.c:13-19', 'resolution': 'Do not import as original behavior until traced against the running game.'},
            'widthExample': {'scenarioIndex': 2, 'cityIndex': 18, 'rawOffset': f'0x{pointers[8] + 18*32 + 8:x}', 'rawU16': raw_xuchang, 'multipliedBy100': raw_xuchang*100, 'storageObservation': 'city loader writes 32-bit result; field meaning/display requires independent trace'},
            'releaseReady': False, 'limitations': ['Checks selected bytes only; field meanings and complete gameplay are not certified.', 'City province, terrain, tier and neighbors are human-authored candidates.', 'The six scenario months and titles are not validated by metadata byte equality.', 'The battlefield indexing conflict and unscaled screenshots require further research.']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom', required=True, type=Path)
    p.add_argument('--candidate-dir', required=True, type=Path)
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    try:
        result = audit(args.rom, args.candidate_dir)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print('AUDIT ERROR: ' + str(exc), file=sys.stderr)
        return 2
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding='utf-8')
    else:
        print(text, end='')
    return 1 if result['candidateByteMismatches'] else 0


if __name__ == '__main__':
    sys.exit(main())
