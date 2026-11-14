"""A glider in slot 0 (the slot the game treats as Chip) and another glider (or a block) running into each other.
Fixed corridors with gaps 1-5 (both parities) plus random open rooms. No joystick input, tick-0 A start.
Lock-step cartridge vs remake; prints what slot 0 and slot 1 do around the meeting."""
import sys, random, collections
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
G, B = 5, 7
TICKS = 60

def track(snap):
    if snap == 'crash': return 'CRASH'
    A = bytes.fromhex(snap)
    return [(A[i], A[128 + i] // 8, A[256 + i] // 8) for i in range(2)]

def run(name, cells, objs):
    r = C.run_both(M.level(cells, objs), {}, TICKS, start=True)
    if r is None: return name, 'no start', []
    m, le, lc, el, cl = r; ns = C.run_both.outofsync
    ok = m == le == lc
    st = 'sync' if ok else ('flagged' if ns is not None and ns <= m else 'DIFF @%d' % m)
    return name, st, [track(s) for s in el]

def corridor_h(gap, t1=G, t0=G):
    # slot 0 is turned south at level start; south is wall, so a glider turns left (east) into the corridor
    cells = {(x, 10): 0 for x in range(4, 28)}
    return cells, [((t0 << 2) | M.E, 8, 10), ((t1 << 2) | M.W, 8 + gap + 1, 10)]

def corridor_v(gap, t1=G, t0=G):
    cells = {(10, y): 0 for y in range(2, 28)}
    return cells, [((t0 << 2) | M.S, 10, 6), ((t1 << 2) | M.N, 10, 6 + gap + 1)]

def chase(gap):
    # slot-1 glider behind slot 0, both heading east, slot 0 stops at a dead end
    cells = {(x, 10): 0 for x in range(4, 14)}
    return cells, [((G << 2) | M.E, 12 - gap - 1, 10), ((G << 2) | M.E, 12 - 2 * gap - 2, 10)]

res = []
for gap in range(0, 6):
    res.append(run('H glider/glider gap %d' % gap, *corridor_h(gap)))
    res.append(run('V glider/glider gap %d' % gap, *corridor_v(gap)))
    res.append(run('H slot0 glider / block gap %d' % gap, *corridor_h(gap, t1=B)))
    res.append(run('H slot0 block / glider gap %d' % gap, *corridor_h(gap, t0=B)))
for gap in range(0, 4):
    res.append(run('chase gap %d' % gap, *chase(gap)))

detail = '-v' in sys.argv
for name, st, tr in res:
    print('%-32s %s' % (name, st))
    if detail:
        prev = None
        for k, t in enumerate(tr):
            if t != prev: print('     t%-3d %s' % (k, t))
            prev = t

# random open rooms: two gliders (slot 0 and 1), sometimes more monsters
rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 1)
cnt = collections.Counter()
for it in range(150):
    w, h = rng.randrange(3, 9), rng.randrange(3, 9)
    cells = {(x, y): (0 if rng.random() < 0.85 else 1) for x in range(8, 8 + w) for y in range(8, 8 + h)}
    free = [c for c, v in cells.items() if v == 0]; rng.shuffle(free)
    if len(free) < 3: continue
    objs = [((G << 2) | rng.randrange(4), *free[0]), ((G << 2) | rng.randrange(4), *free[1])]
    for c in free[2:2 + rng.randrange(0, 3)]: objs.append(((rng.choice([2, 3, 4, 5, 6, 7, 8, 11]) << 2) | rng.randrange(4), *c))
    _, st, tr = run('rand', cells, objs)
    cnt[st.split(' @')[0]] += 1
    if st.startswith('DIFF'): print(' random DIFF it=%d %s' % (it, st))
print('random rooms:', dict(cnt))
