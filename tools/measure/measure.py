"""Black-box measurement of the original's behaviour for tile codes / object types / effect frames that the
cartridge only reaches through off-map writes.  Every fact is obtained by building a small test level, running
it on the emulated cartridge and *observing* what happens (positions, map cells, crash / no crash).
No program bytes are read.

usage: python3 measure.py OUT.json
"""
import sys, json
sys.path.insert(0, '/home/claude/verify')
from inject_run import inject
from clynx import CLynx

N, E, S, W = 0, 1, 2, 3
DX = [0, 1, 0, -1]; DY = [-1, 0, 1, 0]

from lockstep import JOY
import doc_engine as DE
JOYB = {N: JOY[DE.N], E: JOY[DE.E], S: JOY[DE.S], W: JOY[DE.W]}

def level(cells, objs, title=b'\x0c'):
    """cells: {(x,y): code} (rest wall); objs: list of (state, x, y) in slot order (slot 0 = Chip)."""
    m = bytearray([1] * 1024)
    for (x, y), t in cells.items(): m[y * 32 + x] = t
    st = bytearray(128); xs = bytearray(128); ys = bytearray(128)
    for i, (s, x, y) in enumerate(objs): st[i] = s; xs[i] = x * 8; ys[i] = y * 8
    return bytes(m) + bytes(st) + bytes(xs) + bytes(ys) + b'\0\0' + title + b'\0'

class Run:
    """Starts the level; tick(dir) runs one game tick and returns False if the original hangs or crashes."""
    def __init__(s, data, boots=None):
        s.L = CLynx('/home/claude/rom/st_i.pkl'); inject(s.L, data)
        s.L.ram[0x0A] = 0; s.L.ram[0x3E] = 1; s.L.ram[0x39] = 10; s.L.joy = 0
        s.ok = s.L.run_to([0x39DF], 4_000_000) and s.L.run_to([0x3A11], 4_000_000)
        if s.ok and boots:
            for k, v in boots.items(): s.L.ram[k] = v
    def tick(s, d=None):
        if not s.ok: return False
        s.L.joy = JOYB[d] if d is not None else 0
        try: s.ok = s.L.run_to([0x3A11], 4_000_000)
        except RuntimeError: s.ok = False
        return s.ok
    r = property(lambda s: s.L.ram)
    def state(s, i): return s.r[0x1000 + i]
    def pos(s, i): return s.r[0x1080 + i], s.r[0x1100 + i]
    def cell(s, x, y): return s.r[0x0C00 + y * 32 + x]
    def under(s, i): return s.r[0x1200 + i]

# 3x3 blocks on a 10x10 grid inside the map; block k has its centre at:
# Kept out of the camera's view (Chip sits at the bottom-right, so the drawn window is columns/rows 23..31):
# drawing tile codes past the real tile set runs stray code (see display_run), which would spoil the test.
def centre(k): return 2 + 3 * (k % 7), 2 + 3 * (k // 7)
CHIP = (29, 29)

def entry_run(code, chip_dir, types=range(2, 16), boots=None):
    """One run: Chip (slot 0) faces `code` in chip_dir and pushes that way on tick 0; every monster type in
    `types`, moving in each direction, faces its own cell holding `code`."""
    cells = {}; objs = []; tests = []
    cx, cy = CHIP
    cells[(cx, cy)] = 0
    if chip_dir is None: chip_dir = N                         # Chip sealed in, only starts the game
    else: cells[(cx + DX[chip_dir], cy + DY[chip_dir])] = code; tests.append((0, 1, chip_dir, (cx, cy)))
    objs.append((0x04 | chip_dir, cx, cy))
    k = 0
    for t in types:
        for d in range(4):
            x, y = centre(k); k += 1
            cells[(x, y)] = 0; cells[(x + DX[d], y + DY[d])] = code
            objs.append((0x80 | (t << 2) | d, x, y))
            tests.append((len(objs) - 1, t, d, (x, y)))
    R = Run(level(cells, objs), boots)
    if not R.ok: return None
    before = {i: R.pos(i) for i, *_ in tests}
    if not R.tick(chip_dir): return 'crash'
    out = []
    for i, t, d, (x, y) in tests:
        tx, ty = x + DX[d], y + DY[d]
        entered = R.cell(tx, ty) == (0x80 | i)
        bx, by = before[i]; ax, ay = R.pos(i)
        out.append(dict(slot=i, type=t, dir=d, enter=entered,
                        dx=(ax - bx + 128) % 256 - 128, dy=(ay - by + 128) % 256 - 128,
                        state=R.state(i), map_after=R.cell(tx, ty)))
    return out

def main(outf):
    res = {}
    # ---- A. which (type, direction) may enter each code, and how far the first step goes
    A = {}
    for code in range(0x80):
        rows = []
        for cd in (None, 0, 1, 2, 3):
            r = entry_run(code, cd, types=range(2, 16) if cd is None else ())
            if r is None: rows = 'level-start-fails'; break
            if r == 'crash': rows += [dict(type=1, dir=cd, enter=None, crash=True)]; continue
            rows += r
        A[code] = rows
        print('code %02X' % code, rows if isinstance(rows, str) else
              ''.join('X' if x.get('crash') else '1' if x['enter'] else '.' for x in rows), flush=True)
    res['entry'] = A
    json.dump(res, open(outf, 'w'))

if __name__ == '__main__':
    main(sys.argv[1])

def display_run(code, near=True, ticks=3):
    """Chip sealed in; `code` sits on a cell in view (two cells east) that nothing touches."""
    cx, cy = 15, 15
    cells = {(cx, cy): 0, (cx + 2, cy): code} if near else {(cx, cy): 0}
    R = Run(level(cells, [(0x04 | S, cx, cy)]))
    if not R.ok: return 'level-start-fails'
    for t in range(ticks):
        if not R.tick(N if t == 0 else None): return 'crash@%d' % t
    return 'ok'

def entry_single(code, t, d):
    """One monster of type t moving in direction d into `code`; result dict, or 'crash'."""
    r = entry_run(code, None, types=())
    cells = {CHIP: 0}; x, y = centre(0)
    cells[(x, y)] = 0; cells[(x + DX[d], y + DY[d])] = code
    R = Run(level(cells, [(0x04 | N, *CHIP), (0x80 | (t << 2) | d, x, y)]))
    if not R.ok: return None
    b = R.pos(1)
    if not R.tick(N): return 'crash'
    a = R.pos(1)
    return dict(type=t, dir=d, enter=R.cell(x + DX[d], y + DY[d]) == 0x81,
                dx=(a[0] - b[0] + 128) % 256 - 128, dy=(a[1] - b[1] + 128) % 256 - 128, state=R.state(1))

def step_table():
    """First-tick displacement of types 12..15 moving on floor / ice / force floor."""
    out = {}
    for code in (0x00, 0x02, 0x05):
        for t in range(12, 16):
            for d in range(4):
                r = entry_single(code, t, d)
                out[(code, t, d)] = r if r == 'crash' else (r['dx'], r['dy'], r['enter'])
    return out

def effect_frames():
    """For each frame f (state 0x40|f) the state the original stores on the next odd tick."""
    res = {}
    fs = list(range(0x00, 0x40))
    for chunk in (fs[:32], fs[32:]):
        cells = {CHIP: 0}; objs = [(0x04 | N, *CHIP)]
        for k, f in enumerate(chunk):
            x, y = centre(k); cells[(x, y)] = 0; objs.append((0x40 | f, x, y))
        R = Run(level(cells, objs))
        prev = [R.state(i) for i in range(len(objs))]
        for t in range(4):
            tk = R.r[0x2F]
            if not R.tick(N if t == 0 else None): res['crash'] = (chunk[0], t); break
            for k, f in enumerate(chunk):
                s = R.state(k + 1)
                if f not in res and s != prev[k + 1]:
                    x, y = centre(k)
                    res[f] = dict(next=s, tick=tk, cell=R.cell(x, y))
            prev = [R.state(i) for i in range(len(objs))]
    return res

def arrival(code, t, d, chip=False, ticks=12):
    """Mover enters `code` and arrives on it.  Returns ('crash', tick) or ('ok', diffs vs a floor run)."""
    def go(c):
        cells = {CHIP: 0}; x, y = centre(0)
        cells[(x, y)] = 0; cells[(x + DX[d], y + DY[d])] = c
        if chip:
            cx, cy = CHIP
            cells[(cx + DX[d], cy + DY[d])] = c
            objs = [(0x04 | d, cx, cy)]
        else:
            objs = [(0x04 | N, *CHIP), (0x80 | (t << 2) | d, x, y)]
        R = Run(level(cells, objs))
        for k in range(ticks):
            if not R.tick((d if chip else N) if k == 0 else None): return ('crash', k), None
        return ('ok', None), bytes(R.L.ram[0:0x1300])
    r, ram = go(code)
    if r[0] == 'crash': return r
    _, base = go(0)
    return ('ok', [hex(i) for i in range(0x1300) if ram[i] != base[i] and not 0x0C00 <= i < 0x1000][:12])

def room_run(code, mover, d, inputs=None, ticks=14, boots=None):
    """Open 5x5 floor room with `code` in the middle; mover (type, or 1 = Chip) starts one cell away and moves
    in direction d onto it.  Returns list of per-tick (state, x, y, under, cell_of_code) or ends with 'crash'."""
    cx, cy = (8, 8) if mover != 1 else (26, 26)
    cells = {(x, y): 0 for x in range(cx - 2, cx + 3) for y in range(cy - 2, cy + 3)}
    cells[(cx, cy)] = code
    sx, sy = cx - DX[d], cy - DY[d]
    if mover == 1:
        objs = [(0x04 | d, sx, sy)]; sl = 0
    else:
        cells[CHIP] = 0; objs = [(0x04 | N, *CHIP), (0x80 | (mover << 2) | d, sx, sy)]; sl = 1
    R = Run(level(cells, objs), boots)
    if not R.ok: return None
    log = []
    for k in range(ticks):
        inp = (inputs or {}).get(k, d if (mover == 1 and k == 0) else (N if k == 0 else None))
        if not R.tick(inp): log.append('crash'); break
        log.append((R.state(sl), *R.pos(sl), R.under(sl), R.cell(cx, cy)))
    return log

def objref_run(j, d_leave=None, boots=None, ticks=10):
    """Chip walks east onto a cell that references slot j (a Chip-type object parked on a trap), so Chip's
    under-tile becomes the object reference 0x80|j.  Optionally tries to leave in d_leave at tick 5."""
    cx, cy = 20, 20
    cells = {(x, y): 0 for x in range(cx - 1, cx + 4) for y in range(cy - 2, cy + 3)}
    cells[(cx + 1, cy)] = 0x2D                       # trap holding slot j
    objs = [(0x04 | E, cx, cy)] + [(0, 0, 0)] * (j - 1) + [(0x04 | N, cx + 1, cy)]
    R = Run(level(cells, objs), boots)
    if not R.ok: return None
    log = []
    for k in range(ticks):
        inp = E if k == 0 else (d_leave if (d_leave is not None and k == 5) else None)
        if not R.tick(inp): log.append('crash'); break
        log.append((R.state(0), *R.pos(0), R.under(0)))
    return log

def objref_props(V):
    """Behaviour of the byte value V (0x80..0xFF) used as a tile: leave mask, ice bounce, entry by class."""
    res = {}
    # leave / ice: four tanks (forward only) standing on V, one per direction, floor all around
    base = 1 if (V & 0x7F) >= 64 else 100           # keep the test slots away from the slot V refers to
    cells = {CHIP: 0}; objs = [(0x04 | N, *CHIP)] + [(0, 0, 0)] * (base - 1)
    for d in range(4):
        x, y = 4 + 6 * d, 5
        for xx in range(x - 1, x + 2):
            for yy in range(y - 1, y + 2): cells[(xx, yy)] = 0
        objs.append((0x80 | (8 << 2) | d, x, y))
    R = Run(level(cells, objs))
    for d in range(4): R.r[0x1200 + base + d] = V
    if not R.tick(N): res['leave'] = 'crash'
    else:
        lv = []
        for d in range(4):
            x0, y0 = (4 + 6 * d) * 8, 5 * 8
            x, y = R.pos(base + d); st = R.state(base + d)
            if (x, y) != (x0, y0): lv.append('pass' if (st & 3) == d else 'bounce-moved')
            else: lv.append('bounce' if (st & 3) == (d ^ 2) else 'stay' if st & 0x80 else 'stopped')
        res['leave'] = lv
    # entry: a monster of class bug(2) / fireball(4) / block(7) moving into Chip, whose under is V.
    # Chip is walled in and pushes away from the monster (into a wall) only to start the game.
    ent = {}
    for t in (2, 4, 7):
        for d in range(4):
            cx, cy = 15, 15
            mx, my = cx - DX[d], cy - DY[d]
            ms = 1 if (V & 0x7F) != 1 else 2
            R = Run(level({(cx, cy): 0, (mx, my): 0}, [(0x04 | N, cx, cy)] + [(0, 0, 0)] * (ms - 1) + [(0x80 | (t << 2) | d, mx, my)]))
            R.r[0x1200] = V
            if not R.tick(d): ent[(t, d)] = 'crash'; continue
            ent[(t, d)] = 'kill' if R.state(0) & 0x40 else 'no'
    # Chip class: Chip moving into a Chip-type object (passable as an object) whose under is V
    for d in range(4):
        cx, cy = 15, 15
        tx, ty = cx + DX[d], cy + DY[d]
        js = 50 if (V & 0x7F) != 50 else 51
        p = (d + 1) % 4                      # the parked object faces a side wall, never Chip
        R = Run(level({(cx, cy): 0, (tx, ty): 0x2D}, [(0x04 | d, cx, cy)] + [(0, 0, 0)] * (js - 1) + [(0x04 | p, tx, ty)]))
        R.r[0x1200 + js] = V
        if not R.tick(d): ent[(1, d)] = 'crash'; continue
        ent[(1, d)] = 'pass' if R.pos(0) != (cx * 8, cy * 8) else 'no'
    res['entry'] = {'%d,%d' % k: v for k, v in ent.items()}
    return res


def objref_all():
    out = {}
    for V in range(0x80, 0x100):
        r = objref_props(V)
        j = (V & 0x7F) or None
        sl = []
        if j:
            for boots in (None, {0x20: 1}):
                log = objref_run(j, boots=boots, ticks=6)
                sl.append('crash' if 'crash' in log else abs(log[0][1] - 160))
        r['onto'] = sl
        out[V] = r
        print('%02X' % V, r['leave'], ''.join(v[0] for v in r['entry'].values()), sl, flush=True)
    return out


def effect_frames_open():
    """As effect_frames, but each effect alone in an open 5x5 floor room (a new live state may start moving at
    once; in a walled pocket that move is blocked and the moving flag cleared again)."""
    res = {}
    for f in range(0x40):
        cells = {(x, y): 0 for x in range(6, 11) for y in range(6, 11)}; cells[CHIP] = 0
        R = Run(level(cells, [(0x04 | N, *CHIP), (0x40 | f, 8, 8)]))
        prev = R.state(1)
        for t in range(4):
            tk = R.r[0x2F]
            if not R.tick(N if t == 0 else None): res[f] = dict(next=None, crash=t); break
            s = R.state(1)
            if s != prev:
                res[f] = dict(next=s, tick=tk, cell=R.cell(8, 8), pos=R.pos(1)); break
    return res
