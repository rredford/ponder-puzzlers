"""Extended mode: are the north/west thin walls (codes 34/35, DAT 06/07) exact mirrors of the south/east ones?
Random rooms with thin-wall edges written two ways - A: south/east wall on the upper/left cell, B: north/west wall
on the lower/right cell - and the same objects and input; the remake (extended mode) must move every object
identically in both."""
import sys, struct, random, subprocess, tempfile
LP = '/home/claude/remake/build/levelpack'
MON = {2: 0x40, 4: 0x44, 6: 0x48, 8: 0x4C, 5: 0x50, 11: 0x54, 9: 0x58, 10: 0x5C, 3: 0x60}   # + N W S E
def rle(cells):
    out = bytearray(); i = 0
    while i < len(cells):
        j = i
        while j < len(cells) and cells[j] == cells[i] and j - i < 255: j += 1
        out += bytes([0xFF, j - i, cells[i]]) if j - i >= 4 else bytes(cells[i:j]); i = j
    return bytes(out)
def dat(top, monsters):
    l1 = rle(top); l2 = rle([0] * 1024)
    t = b'T'; f = bytes([3, len(t) + 1]) + t + b'\0'
    if monsters: f += bytes([10, 2 * len(monsters)]) + bytes(b for m in monsters for b in m)
    body = struct.pack('<HHHH', 1, 0, 0, 1) + struct.pack('<H', len(l1)) + l1 + struct.pack('<H', len(l2)) + l2 + struct.pack('<H', len(f)) + f
    return struct.pack('<IH', 0x0102AAAC, 1) + struct.pack('<H', len(body)) + body
def scenario(rng):
    X0, Y0, N = 10, 10, 12
    base = [1] * 1024
    inside = [(x, y) for x in range(X0, X0 + N) for y in range(Y0, Y0 + N)]
    for x, y in inside: base[y * 32 + x] = 0
    A = list(base); B = list(base); used = set()
    for _ in range(rng.randrange(6, 22)):
        x, y = rng.choice(inside)
        if rng.random() < 0.5:     # horizontal edge between (x,y-1) and (x,y)
            if y == Y0 or (x, y - 1) in used or (x, y) in used: continue
            A[(y - 1) * 32 + x] = 0x08; B[y * 32 + x] = 0x06
        else:                      # vertical edge between (x-1,y) and (x,y)
            if x == X0 or (x - 1, y) in used or (x, y) in used: continue
            A[y * 32 + x - 1] = 0x09; B[y * 32 + x] = 0x07
        used |= {(x, y), (x, y - 1), (x - 1, y)}
    free = [c for c in inside if c not in used]; rng.shuffle(free)
    cx, cy = free.pop(); A[cy * 32 + cx] = B[cy * 32 + cx] = 0x6C + rng.randrange(4)
    mons = []
    for _ in range(rng.randrange(1, 6)):
        x, y = free.pop(); t = rng.choice(list(MON)); v = MON[t] + rng.randrange(4)
        A[y * 32 + x] = B[y * 32 + x] = v; mons.append((x, y))
    for _ in range(rng.randrange(0, 3)):
        x, y = free.pop(); A[y * 32 + x] = B[y * 32 + x] = 0x0A           # block
    ticks = ['tick %x' % (rng.choice([1, 2, 4, 8, 0, 0]) if rng.random() < 0.4 else 0) for _ in range(80)]
    return dat(A, mons), dat(B, mons), ticks
def run(datb, ticks):
    with tempfile.TemporaryDirectory() as td:
        open(td + '/l.dat', 'wb').write(datb); open(td + '/s.txt', 'w').write('tick 10\n' + '\n'.join(ticks) + '\n')
        out = subprocess.run([LP, 'raw', td + '/l.dat', td + '/s.txt', '--extended'], capture_output=True, text=True).stdout.split('\n')
    # keep slot state, x, y (the map differs on purpose)
    return [''.join(l.split()[3:6]) for l in out if l.startswith('T ')]
if __name__ == '__main__':
    rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1); n = int(sys.argv[1])
    same = 0; bad = []; moved = 0
    for it in range(n):
        a, b, ticks = scenario(rng); ra, rb = run(a, ticks), run(b, ticks)
        if ra and ra == rb: same += 1
        else: bad.append((it, next((k for k, (p, q) in enumerate(zip(ra, rb)) if p != q), None), len(ra), len(rb)))
        moved += ra[0] != ra[-1] if ra else 0
    print('%d scenarios: identical in %d (objects moved in %d)' % (n, same, moved))
    for b in bad[:10]: print('DIFF scenario %d first differing tick %s (lengths %d/%d)' % b)
