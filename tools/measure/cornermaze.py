"""Build a 32x32 test level: walls round the edge, the interior an ice-corner maze in which every corner turns
Chip, so one push from the start sends him sliding over every ice corner in turn and onto the exit.
Path search: random Warnsdorff walks where each step must be perpendicular to the previous one.
usage: cornermaze.py OUT.bin [SEED] [TRIES]"""
import sys, random
DX = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}           # N E S W
# corner code by (direction arriving, direction leaving)  (doc 03 §3.3)
CORNER = {(1, 2): 0x0B, (0, 3): 0x0B, (2, 1): 0x0D, (3, 0): 0x0D,
          (2, 3): 0x0C, (1, 0): 0x0C, (0, 1): 0x0A, (3, 2): 0x0A}
def inside(x, y): return 1 <= x <= 30 and 1 <= y <= 30
def walk(rng, start, d0):
    used = {start}
    x, y = start
    nx, ny = x + DX[d0][0], y + DX[d0][1]
    path = [(nx, ny)]; dirs = [d0]; used.add((nx, ny))
    while True:
        d = dirs[-1]; cx, cy = path[-1]
        opts = []
        for nd in ((d + 1) % 4, (d + 3) % 4):
            px, py = cx + DX[nd][0], cy + DX[nd][1]
            if inside(px, py) and (px, py) not in used:
                deg = sum(1 for d2 in ((nd + 1) % 4, (nd + 3) % 4)
                          if inside(px + DX[d2][0], py + DX[d2][1]) and (px + DX[d2][0], py + DX[d2][1]) not in used)
                opts.append((deg, rng.random(), nd, (px, py)))
        if not opts: break
        opts.sort()
        deg, _, nd, p = opts[0] if opts[0][0] > 0 or len(opts) == 1 else opts[-1] if opts[-1][0] > 0 else opts[0]
        path.append(p); dirs.append(nd); used.add(p)
    return path, dirs
def best(seed, tries):
    rng = random.Random(seed); top = None
    for t in range(tries):
        start = (rng.randrange(1, 31), rng.randrange(1, 31)); d0 = rng.randrange(4)
        sx, sy = start[0] + DX[d0][0], start[1] + DX[d0][1]
        if not inside(sx, sy): continue
        path, dirs = walk(rng, start, d0)
        # the last cell becomes the exit (entered by a turn from the corner before it)
        if len(path) < 3: continue
        if top is None or len(path) > len(top[1]): top = (start, path, dirs)
    return top
def level(start, path, dirs):
    m = bytearray([1] * 1024)
    corners = path[:-1]; ex = path[-1]
    for i, (x, y) in enumerate(corners):
        m[y * 32 + x] = CORNER[(dirs[i], dirs[i + 1])]
    m[start[1] * 32 + start[0]] = 0x00
    m[ex[1] * 32 + ex[0]] = 0x25
    st = bytearray(128); xs = bytearray(128); ys = bytearray(128)
    st[0] = 0x04 | dirs[0]; xs[0] = start[0] * 8; ys[0] = start[1] * 8
    return bytes(m) + bytes(st) + bytes(xs) + bytes(ys) + b'\0\0' + b'\x0c' + b'\0', len(corners)
if __name__ == '__main__':
    out = sys.argv[1]; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1; tries = int(sys.argv[3]) if len(sys.argv) > 3 else 4000
    start, path, dirs = best(seed, tries)
    data, n = level(start, path, dirs)
    open(out, 'wb').write(data)
    print('corners on the path: %d of 900 interior cells; start %s, first push %s, exit %s' % (n, start, 'NESW'[dirs[0]], path[-1]))
    for y in range(32): print(''.join({1: '#', 0: 'C', 0x25: 'E', 0x0A: '┌', 0x0B: '┐', 0x0C: '┘', 0x0D: '└'}.get(data[y * 32 + x], '?') for x in range(32)))
