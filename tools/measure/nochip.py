"""A level with no Chip: slot 0 empty (state 0) at (0,0), a monster (slot 1) running along row 0 toward (0,0).
(0,0) holds a bomb or floor. Started with A (no movement) or with a direction key, or Chip placed in slot 2.
Lock-step cartridge vs remake; prints slot 0-2 and map (0,0) whenever they change, plus the remake's outcome."""
import sys
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
TICKS = 80
MON = {'glider': 5, 'tank': 8, 'ball': 6, 'block': 7}

def view(snap):
    if snap == 'crash': return 'CRASH'
    A = bytes.fromhex(snap)
    return tuple((hex(A[i]), A[128 + i] // 8, A[256 + i] // 8) for i in range(3)) + ('map00=%02x' % A[512],)

def run(name, cells, objs, inputs, start):
    r = C.run_both(M.level(cells, objs), inputs, TICKS, start=start)
    if r is None: print('%-40s no start' % name); return
    m, le, lc, el, cl = r; ns = C.run_both.outofsync
    st = 'sync' if m == le == lc else ('flagged' if ns is not None and ns <= m else 'DIFF @%d %s' % (m, C.describe(el[m], cl[m]) if m < min(le, lc) else ''))
    print('%-40s %-6s remake outcome %s' % (name, st, C.run_both.outcome))
    if '-v' in sys.argv:
        prev = None
        for k, s in enumerate(el):
            v = view(s)
            if v != prev: print('     t%-3d %s' % (k, v))
            prev = v

for mon, mt in MON.items():
    for under in ('bomb', 'floor'):
        cells = {(x, 0): 0 for x in range(0, 12)}
        if under == 'bomb': cells[(0, 0)] = 0x2C
        cells[(6, 1)] = 0   # side pocket so a turning monster has somewhere to go
        objs = [(0, 0, 0), ((mt << 2) | M.W, 6, 0)]
        if mon == 'block': objs[1] = ((mt << 2) | M.W, 6, 0); objs.append(((5 << 2) | M.W, 8, 0))   # glider pushes? no: blocks only move by Chip/force; use force floor below
        run('%s -> (0,0) %s, A start' % (mon, under), cells, objs, {}, True)
        run('%s -> (0,0) %s, key start (E)' % (mon, under), cells, objs, {0: {M.E}}, False)
        run('%s -> (0,0) %s, key held E' % (mon, under), cells, objs, {k: {M.E} for k in range(TICKS)}, False)

# Chip present but not in slot 0
cells = {(x, y): 0 for x in range(4, 12) for y in range(4, 8)}; cells[(10, 6)] = 0x2C
objs = [(0, 0, 0), ((5 << 2) | M.E, 5, 5), ((1 << 2) | M.S, 6, 6)]
run('Chip in slot 2, A start, key E held', cells, objs, {k: {M.E} for k in range(TICKS)}, True)
run('Chip in slot 2, key start E held', cells, objs, {k: {M.E} for k in range(TICKS)}, False)
