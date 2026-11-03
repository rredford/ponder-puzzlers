"""Code 71 with both ways out blocked ("acting wall, 71, acting wall"): Chip steps from a recessed wall (which
turns into a wall behind him) onto 71, and the cell ahead is an acting wall of a given kind.  Original vs
remake, lock-step; prints Chip's state/position per tick on the original."""
import sys
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
DX = {M.N: (0, -1), M.E: (1, 0), M.S: (0, 1), M.W: (-1, 0)}
def scenario(d, ahead, behind=0x16, boots=None, T=14):
    cx, cy = 15, 15
    dx, dy = DX[d]
    cells = {(x, y): 0 for x in range(32) for y in range(32)}
    cells[(cx - dx, cy - dy)] = behind          # Chip starts here
    cells[(cx, cy)] = 0x71
    cells[(cx + dx, cy + dy)] = ahead
    objs = [(0x04 | d, cx - dx, cy - dy)]
    data = M.level(cells, objs)
    inputs = {0: {d}}
    return data, inputs
def trace(data, inputs, T=14, boots=None):
    R = M.Run(data, boots); out = []
    for k in range(T):
        jb = 0
        for e in inputs.get(k, ()): jb |= M.JOYB[e]
        R.L.joy = jb
        try: ok = R.L.run_to([0x3A11], 4_000_000)
        except RuntimeError: ok = False
        if not ok: out.append('X'); break
        out.append('%02x@%d,%d' % (R.r[0x1000], R.r[0x1080], R.r[0x1100]))
    return out
if __name__ == '__main__':
    for d in (M.N, M.E, M.S, M.W):
        for ahead, name in ((1, 'wall'), (0x27, 'invisible'), (0x32, 'blue wall'), (0x26, 'hidden'), (0x18, 'toggle closed'), (0x24, 'socket'), (0x00, 'floor')):
            data, inputs = scenario(d, ahead)
            m, le, lc, el, cl = C.run_both(data, inputs, 14)
            print('%s ahead=%-13s %s  %s' % ('NESW'[d], name, 'MATCH' if m == le == lc else 'DIFF@%d' % m, ' '.join(trace(data, inputs)[:12])))
