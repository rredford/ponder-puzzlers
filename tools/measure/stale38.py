"""Code 38 at x = 96 (stale cell lookup, doc 04 §4.4): which cell does Chip's move use, depending on what Chip
did on the ticks before?  Open map, Chip mid-map, the damaged byte put in place directly (no 38 on screen).
For every tick on which a new reference to Chip appears on the map, report whether it lies next to Chip's real
cell or next to the stale cell (the cell above the drawn window's top-right; Chip's cell before the first frame)."""
import sys; sys.path.insert(0, '/home/claude/verify'); import measure as M
DX = {0: 0, 1: 1, 2: 0, 3: -1}; DY = {0: -1, 1: 0, 2: 1, 3: 0}
def stale_after_draw(R):
    qx, qy = R.r[0x1080] // 2, R.r[0x1100] // 2
    cx = min(max(qx - 16, 0), 93); cy = min(max(qy - 16, 0), 93)
    return (cy // 4 - 2) * 32 + cx // 4 - 1 + 10
def run(inputs, T=14, start=(15, 15), walls=(), objs_extra=()):
    cells = {(x, y): 0 for x in range(32) for y in range(32)}
    for w in walls: cells[w] = 1
    R = M.Run(M.level(cells, [(0x04 | M.N, *start)] + list(objs_extra)))
    R.L.ram[0x3DE2] = 0x60
    stale = start[1] * 32 + start[0]
    out = []
    for k in range(T):
        before = bytes(R.r[0xC00:0x1000])
        real = (R.r[0x1100] // 8) * 32 + R.r[0x1080] // 8
        aligned = R.r[0x1080] % 8 == 0 and R.r[0x1100] % 8 == 0
        d = inputs.get(k)
        ok = R.tick(d)
        R.L.ram[0x3DE2] = 0x60
        if not ok: out.append((k, 'crash')); break
        after = bytes(R.r[0xC00:0x1000])
        new = [c for c in range(1024) if after[c] == 0x80 and before[c] != 0x80]
        tag = []
        for c in new:
            what = '?'
            for dd in range(4):
                if c == real + DX[dd] + 32 * DY[dd]: what = 'real+%s' % 'NESW'[dd]
                if c == stale + DX[dd] + 32 * DY[dd]: what = ('both+' if what != '?' else 'stale+') + 'NESW'[dd]
            tag.append(what)
        out.append((k, 'NESW'[d] if d is not None else '-', 'st%02x' % R.r[0x1000], tag))
        stale = stale_after_draw(R)
    return out
H = {
 'idle, then press E':              {3: M.E},
 'E at 0, arrive, idle, press N':   {0: M.E, 6: M.N},
 'E held 0..9 (continue)':          {k: M.E for k in range(10)},
 'E 0..3, then S 4..6 (turn)':      {**{k: M.E for k in range(4)}, **{k: M.S for k in range(4, 7)}},
 'N into wall 0..2, then E':        {0: M.N, 1: M.N, 2: M.N, 3: M.E},
 'N into wall 0, idle, then E':     {0: M.N, 3: M.E},
 'N into wall 0..2, then S (back)': {0: M.N, 1: M.N, 2: M.N, 3: M.S},
}
if __name__ == '__main__':
    for name, inp in H.items():
        walls = [(15, 14)] if 'wall' in name else []
        res = [r for r in run(inp, walls=walls) if len(r) < 4 or r[3] or r[1] != '-']
        print(name); [print('   ', r) for r in res]
