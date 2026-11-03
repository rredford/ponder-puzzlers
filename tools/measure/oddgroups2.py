"""Oddity 2, grouped sweep, step 2: Chip walks E/W, a ball bounces in view, the odd code sits in view.
Per code: crash tick, and the first tick where game state (map, object tables, zero-page game vars 20-2F,
link table) differs from a control run, ignoring the 4 bytes A..A+3 the drawing write lands on."""
import sys, json; sys.path.insert(0, '/home/claude/verify'); import measure as M
from oddgroups import A
CX, CY = 15, 15
def run(code, c, r, T=40):
    cells = {(x, y): 0 for x in range(11, 20) for y in range(12, 19)}
    for x in range(11, 20): cells[(x, 17)] = 0
    cells[(10, 17)] = 1; cells[(20, 17)] = 1
    cells[(c, r)] = code
    objs = [(0x04 | M.E, CX, CY), (0x80 | (6 << 2) | M.E, 13, 17)]
    R = M.Run(M.level(cells, objs))
    out = []
    for k in range(T):
        d = M.E if (k // 6) % 2 == 0 else M.W
        if not R.tick(d): return k, out
        out.append(bytes(R.L.ram))
    return None, out
REG = [(0x20, 0x30), (0x400, 0xC00), (0xC00, 0x1000), (0x1000, 0x1300), (0x3D73, 0x3DDB)]
def first_div(a, b, skip, cell):
    for k in range(min(len(a), len(b))):
        for lo, hi in REG:
            for x in range(lo, hi):
                if x in skip or x == cell: continue
                if a[k][x] != b[k][x]: return k, x
    return None
if __name__ == '__main__':
    codes = sys.argv[1:] or sorted(A)
    res = {}
    for cs in codes:
        code = int(cs, 16); a = A[cs]
        skip = set(range(a, a + 4)) if a is not None else set()
        row = []
        for (c, r) in [(17, 13), (12, 14)]:
            _, base = run(0, c, r)
            crash, sn = run(code, c, r)
            fd = first_div(base, sn, skip, 0xC00 + 32 * r + c)
            hi = None
            if a is not None and sn: hi = tuple(sn[0][a:a + 4])
            row.append(dict(crash=crash, div=fd, w=hi))
        res[cs] = row
        print(cs, 'A=%s' % ('%04X' % a if a is not None else '----'),
              ' | '.join('crash@%s div=%s w=%s' % (x['crash'], ('t%d@%04X' % x['div']) if x['div'] else '-', x['w']) for x in row), flush=True)
    json.dump(res, open('/tmp/claude-0/oddgroups2.json', 'w'))
