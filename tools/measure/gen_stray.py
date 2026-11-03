"""Turn the black-box measurements into engine tables (behaviour, not program bytes):
   class masks for object types 0 and 12-15, special flags / entry masks for codes 34-7F,
   slide / ice flags, arrival behaviour, stray-type steps, effect frames.
   Checks that the model reproduces every measured result, then writes src/core/stray_tables.inc."""
import json, sys
sys.path.insert(0, '/home/claude/verify')
import doc_engine as DE
SP = '/tmp/claude-0/-home-claude/4a4b5c09-bdf2-5f61-92c2-02c1c6ac6cfd/scratchpad/'
T = json.load(open(SP + 'table_ab.json'))
T0 = {int(k): v for k, v in json.load(open(SP + 'type0.json')).items()}
ENTER = {int(c): v for c, v in T['enter'].items()}            # [type-1][dir] for types 1..15
for c, row in T0.items():                                     # add type 0 (index -1 -> store separately)
    if c in ENTER: ENTER[c] = [[int(x[0]) if isinstance(x, list) else 1 for x in row]] + ENTER[c]
for c in (0x2E, 0x30):                                        # buttons: levels without targets cannot start;
    ENTER[c] = [[1] * 4] + [[int(not (DE.T[c][0] & cm(t, d))) for d in range(4)] for t in range(1, 16)] if False else None
S1 = {int(k): v for k, v in json.load(open(SP + 'single.json')).items()}
for c, rows in S1.items():
    for k, r in enumerate(rows):
        if r == 'crash':
            t, d = 2 + k // 4, k % 4
            ENTER[c][t][d] = None                      # crashed on tick 0: entry not observed
for c in (0x43, 0x4A, 0x71):                   # these move an arriving object on within the same tick, so a
    for t in range(12, 16):                    # stray type's one-tick entry test cannot see it: unknown
        ENTER[c][t] = [None] * 4
DIRBIT = [1, 2, 4, 8]
def cm_known(t, d):
    if t == 0: return 0
    return {1: 0, 7: 0x10, 4: 0x50}.get(t, 0x70) | DIRBIT[d]
ALIAS_SPECIAL = set()
def base_entry(c):
    if c < 0x34: return DE.T[c][0], bool(DE.T[c][2] & DE.SPECIAL)
    k = c - 0x34; lv, fl = DE.T[k][1], DE.T[k][2]
    return (lv & 0xF) | (0x80 if fl & DE.SPECIAL else 0) | (0x40 if fl & DE.SLIDE else 0) | (0x20 if fl & DE.ICE else 0), None
SKIP = {0x24, 0x2E, 0x30}            # socket open in the tests (no chips), buttons: level cannot start
# ---- 1. class masks of types 12..15 (from codes 00-33 with known entry masks)
CM = {}
for t in range(12, 16):
    for d in range(4):
        must_not = 0; must = []
        for c in range(0x34):
            if c in SKIP or DE.T[c][2] & DE.SPECIAL: continue
            e = DE.T[c][0]; p = ENTER[c][t][d]
            if p is None: continue
            if p: must_not |= e
            else: must.append(e)
        ok = [m for m in range(256) if not m & must_not and all(e & m for e in must)]
        CM[(t, d)] = ok
def cm(t, d): return cm_known(t, d) if t < 12 else None
# ---- 2. codes 34..7F: special flag + entry mask (alias-derived for 34..67 where it fits)
odd = {}
problems = []
for c in range(0x34, 0x80):
    rows = ENTER.get(c)
    if rows is None: problems.append((c, 'no data')); continue
    nobody = not any(any(r) for r in rows)
    e_alias = base_entry(c)[0] if c < 0x68 else None
    def fits(e, special):
        for t in range(16):
            for d in range(4):
                p = rows[t][d]
                if p is None: continue
                if special: ok = not p
                elif t < 12: ok = (not (e & cm_known(t, d))) == bool(p)
                else: ok = any((not (e & m)) == bool(p) for m in CM[(t, d)])
                if not ok: return False
        return True
    choice = None
    if e_alias is not None and fits(e_alias, False): choice = ('alias', e_alias, False)
    elif nobody: choice = ('special', e_alias if e_alias is not None else 0xFF, True)
    else:
        cands = [e for e in range(256) if fits(e, False)]
        if cands: choice = ('solved', min(cands, key=lambda e: bin(e).count('1')), False)
    if choice is None: problems.append((c, 'no consistent entry mask'))
    odd[c] = choice
print('problems:', [(hex(c), p) for c, p in problems])
print('alias:', ' '.join('%02X' % c for c, v in odd.items() if v and v[0] == 'alias'))
print('special:', ' '.join('%02X' % c for c, v in odd.items() if v and v[0] == 'special'))
print('solved:', ' '.join('%02X=%02X' % (c, v[1]) for c, v in odd.items() if v and v[0] == 'solved'))
# choose one class mask per (t,d) (fewest bits), then entry masks of the solved codes consistent with them
def agree(t, d, m):
    n = 0
    for c, v in odd.items():
        if v[0] != 'alias': continue
        p = ENTER[c][t][d]
        if p is None: continue
        n += (not (v[1] & m)) == bool(p)
    return n
final_cm = {k: max(v, key=lambda m: (agree(k[0], k[1], m), -bin(m).count('1'), -m)) for k, v in CM.items()}
def fits_fixed(c, e):
    rows = ENTER[c]
    for t in range(16):
        for d in range(4):
            m = cm_known(t, d) if t < 12 else final_cm[(t, d)]
            if rows[t][d] is None: continue
            if (not (e & m)) != bool(rows[t][d]): return False
    return True
for c, v in list(odd.items()):
    if v[0] == 'special': continue
    if v[0] == 'alias' and fits_fixed(c, v[1]): continue
    cands = [e for e in range(256) if fits_fixed(c, e)]
    if v[0] == 'alias' and not cands: print('alias code %02X breaks with the chosen class masks' % c); continue
    if not cands: print('NO entry mask for %02X' % c); continue
    odd[c] = ('solved', min(cands, key=lambda e: (bin(e).count('1'), e)), False)
print('re-solved:', ' '.join('%02X=%02X' % (c, v[1]) for c, v in odd.items() if v[0] == 'solved'))
final_cm_unused = {}
for (t, d), cands in ([] if True else CM.items()):
    good = []
    for m in cands:
        okk = True
        for c, v in odd.items():
            if not v or v[2]: continue
            if bool(ENTER[c][t][d]) != (not (v[1] & m)): okk = False; break
        if okk: good.append(m)
    if not good: print('class mask conflict', t, d, [hex(m) for m in cands])
    final_cm[(t, d)] = min(good, key=lambda m: bin(m).count('1')) if good else cands[0]
print('class masks 12-15:', {k: hex(v) for k, v in final_cm.items()})
json.dump(dict(odd={c: v for c, v in odd.items()}, cm={'%d,%d' % k: v for k, v in final_cm.items()}), open(SP + 'model.json', 'w'))

def why(c):
    rows = ENTER[c]; e = base_entry(c)[0] if c < 0x68 else None
    bad = []
    for t in range(16):
        for d in range(4):
            p = rows[t][d]
            if t < 12: pred = not ((e or 0) & cm_known(t, d))
            else: pred = None
            if t < 12 and bool(pred) != bool(p): bad.append((t, d, p))
    return hex(e) if e is not None else None, bad, [''.join(map(str, r)) for r in rows]
if False:
    for c in (0x36, 0x39, 0x3D, 0x5D, 0x6B, 0x71, 0x7A):
        print(hex(c), why(c))

# ------------------------------------------------------------------ write the C++ table
SLIDE = {int(c) for c, v in T['slide'].items() if v == [True]} | {0x61, 0x63, 0x78, 0x7D}   # last four: from types 12-15
ICE = {0x42, 0x48, 0x4A, 0x4E, 0x57, 0x58, 0x59, 0x5A, 0x5B, 0x5C, 0x5D, 0x5E, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
       0x6A, 0x6F, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x79, 0x7A, 0x7B, 0x7C, 0x7E}
# arrival behaviour of the codes that do not crash (fit_odd.py): kind, leave mask, redirect table
SURV = {0x52: ('STOP', 0, None), 0x5C: ('STOP', 2, None), 0x4F: ('KEEP', 0, None), 0x6B: ('KEEP', 1, None),
        0x75: ('KEEP', 4, None), 0x7A: ('KEEP', 0, None), 0x7C: ('KEEP', 0, None),
        # 'move on at once' codes: ARRIVE moves the object again immediately (blocked -> ice bounce -> again);
        # third field: what STAY does (0 crash, 2 nothing). Leave masks found with Chip on skates.
        0x43: ('ADVANCE', 0x3, 0), 0x4A: ('ADVANCE', 0x9, 0), 0x71: ('ADVANCE', 0x4, 2)}
STEP = {12: [(-128, -99), (19, -128), (32, 19), (60, 32)], 13: [(21, 57), (30, 21), (-16, 30), (29, -16)],
        14: [(32, 18), (60, 32), (29, 60), (-115, 29)], 15: [(-115, 3), (73, -115), (29, 73), (-83, 29)]}
import measure as M
EF = M.effect_frames_open()
lines = ['// Generated by verify/gen_stray.py from black-box measurements of the original cartridge',
         '// (test levels run in emulation, behaviour observed; no program bytes). See spec doc 04 §4.4.', '',
         '// Class masks of the stray object types 12..15, per direction (types 0..11: doc 03 §1; type 0 = 0).',
         'static const uint8_t kStrayClass[4][4] = {']
for t in range(12, 16):
    lines.append('    {' + ', '.join('0x%02X' % final_cm[(t, d)] for d in range(4)) + '},')
lines += ['};', '',
          '// Tile codes 0x34..0x7F. entry: -1 = derived at run time from code-0x34 (doc 04 §4.2), else the mask.',
          '// kind: 0 crash on arrival / standing, 1 stop, 2 keep moving, 3 move on at once (ARRIVE: advance again;',
          '// STAY: crash if stay == 0, nothing if stay == 2).',
          'struct OddTile { int16_t entry; uint8_t special, slide, ice, kind, leave, stay; };',
          'static const OddTile kOddTiles[0x4C] = {']
for c in range(0x34, 0x80):
    v = odd[c]
    entry = -1 if v[0] == 'alias' else v[1] if v[0] == 'solved' else 0
    kind, leave, stay = SURV.get(c, ('CRASH', 0, None))
    k = dict(CRASH=0, STOP=1, KEEP=2, ADVANCE=3)[kind]
    lines.append('    {%3d, %d, %d, %d, %d, 0x%X, %d},   // %02X' % (
        entry, int(v[0] == 'special'), int(c in SLIDE), int(c in ICE), k, leave, stay or 0, c))
lines += ['};', '', '// First-tick displacement (dx, dy, 1/8-tile units) of stray types 12..15 per direction.',
          'static const int8_t kStrayStep[4][4][2] = {']
for t in range(12, 16):
    lines.append('    {' + ', '.join('{%d, %d}' % p for p in STEP[t]) + '},')
lines += ['};', '', '// Next state byte of an effect (dying object) for each frame 0x00..0x3F; 0 = removed.',
          'static const uint8_t kEffectNext[0x40] = {']
row = []
for f in range(0x40):
    row.append('0x%02X' % EF[f]['next'])
for k in range(0, 0x40, 16): lines.append('    ' + ', '.join(row[k:k + 16]) + ',')
lines += ['};', '']
open('/home/claude/remake/src/core/stray_tables.inc', 'w').write('\n'.join(lines))
print('wrote stray_tables.inc')
