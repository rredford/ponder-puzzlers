"""Oddity 2, grouped sweep: one representative odd tile code per predicted group (grouped by where the
code's drawing write lands), plus one other member as a check.  For each code and screen position, the
emulated original runs 20 ticks with Chip idle; we record the crash tick and every byte that differs from a
control run (plain floor in the same cell) inside the game-relevant RAM regions."""
import sys, json; sys.path.insert(0, '/home/claude/verify'); import measure as M
CX, CY = 15, 15
REG = [(0x0000, 0x0100, 'zp'), (0x0200, 0x0400, 'p2'), (0x0400, 0x0C00, 'link'), (0x0C00, 0x1000, 'map'),
       (0x1000, 0x1300, 'obj'), (0x3D73, 0x3F73, 'tprop')]
def run(code, c, r, ticks, wait):
    cells = {(CX, CY): 0, (c, r): code, (12, 13): 0}
    objs = [(0x04 | M.N, CX, CY), (0x00 | (8 << 2) | M.N, 12, 13)]   # Chip + one parked tank in view
    R = M.Run(M.level(cells, objs))
    snaps = []
    for k in range(ticks):
        ok = R.tick(None)
        if not ok: return k, snaps
        snaps.append(bytes(R.L.ram[0:0x4000]))
    return None, snaps
def diff(a, b):
    out = []
    for lo, hi, n in REG:
        for x in range(lo, hi):
            if a[x] != b[x] and not (lo == 0 and x in (0x2F,)): out.append(x)
    return out
GROUPS = {
 'sprite blocks':   ['4C', '57'],
 'object tables':   ['3F', '45'],
 'tile props':      ['60', '38'],
 'link high':       ['3D', '7D'],
 'link low':        ['62', '5C'],
 'zero page':       ['41', '35'],
 'page 2':          ['49', '63'],
 'program':         ['61', '43'],
 'high memory':     ['46', '66'],
 'no write':        ['48', '58'],
}
A = {k: (v[0][1][0] if v[0][1] else None) for k, v in json.load(open('/tmp/claude-0/scbaddr.json')).items()}
if __name__ == '__main__':
    T = 20
    res = {}
    for g, codes in GROUPS.items():
        for cs in codes:
            code = int(cs, 16)
            for (c, r) in [(17, 13), (12, 18)]:
                _, base = run(0, c, r, T, 0)
                crash, sn = run(code, c, r, T, 0)
                n = min(len(sn), len(base))
                d = sorted(set(x for k in range(n) for x in diff(base[k], sn[k])))
                a = A[cs]
                hit = None
                if a is not None and a < 0x4000 and sn: hit = (sn[0][a], sn[0][a + 2] if a + 2 < 0x4000 else None)
                res.setdefault(cs, []).append(dict(pos=(c, r), crash=crash, diffs=d[:40], ndiff=len(d), atA=hit))
                print(g, cs, (c, r), 'crash@%s' % crash, 'A=%s' % ('%04X' % a if a is not None else '-'),
                      'atA=%s' % (hit,), 'ndiff=%d' % len(d), ' '.join('%04X' % x for x in d[:16]), flush=True)
    json.dump(res, open('/tmp/claude-0/oddgroups.json', 'w'))
