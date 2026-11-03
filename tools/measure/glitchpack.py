"""Build the small "Lynx glitches" level pack (tests/glitchpack/): levels whose solution needs a non-crash glitch
of the Lynx cartridge, each checked on the original (emulated) and against the remake.  usage: glitchpack.py"""
import sys, struct, os
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
from dat_write import level_record
OUT = '/home/claude/remake/tests/glitchpack'
def walls(): return {(x, y): 1 for x in range(32) for y in range(32)}
def over_the_edge():
    c = walls()
    for x in range(13, 20):
        for y in range(0, 3): c[(x, y)] = 0
    for x in range(13, 20):
        for y in range(28, 32): c[(x, y)] = 0
    c[(16, 29)] = 0x25
    return c, [(0x04 | M.N, 16, 2)], {k: {M.N} for k in range(30)}, \
        'Over the Edge', 'EDGE', 'Sealed in? The Lynx never checks the top edge of the map. Keep walking north.'
def wrap_around():
    c = walls()
    for x in range(0, 3):
        for y in range(14, 17): c[(x, y)] = 0
    for x in range(27, 32): c[(x, 15)] = 0
    c[(31, 14)] = 0
    c[(28, 15)] = 0x25
    return c, [(0x04 | M.W, 1, 15)], {k: {M.W} for k in range(30)}, \
        'Wrap Around', 'WRAP', 'The left edge leads to the right one. Walk west off the map.'
def vanishing_ball():
    c = walls()
    for y in range(0, 6): c[(20, y)] = 0
    for x in range(10, 26): c[(x, 4)] = 0
    c[(25, 4)] = 0x25
    for y in range(27, 32): c[(20, y)] = 0
    inp = {0: {M.N}}
    for k in range(10, 70): inp[k] = {M.E}
    return c, [(0x04 | M.E, 11, 4), (0x80 | (6 << 2) | M.N, 20, 3)], inp, \
        'Vanishing Ball', 'POOF', 'Watch the ball slip off the top of the map. Run east while it is away.'
LEVELS = [over_the_edge, wrap_around, vanishing_ball]
if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    recs = []
    for n, f in enumerate(LEVELS, 1):
        cells, objs, inp, title, pw, hint = f()
        data = M.level(cells, objs)
        open('%s/%d.bin' % (OUT, n), 'wb').write(data)
        # check: the original finishes the level with this input; the remake matches tick for tick
        R = M.Run(data); fin = None
        for k in range(200):
            jb = 0
            for e in inp.get(k, ()): jb |= M.JOYB[e]
            R.L.joy = jb
            if not R.L.run_to([0x3A11], 4_000_000): break
            if R.r[0x28]: fin = k; break
        r = C.run_both(data, inp, (fin or 150) + 5)
        print('%d %-15s original finishes at tick %s; remake matches %d of %d ticks' % (n, title, fin, r[0], r[1]))
        recs.append(level_record(n, data, title, pw, 0, hint))
    dat = struct.pack('<IH', 0x0102AAAC, len(recs)) + b''.join(recs)
    open(OUT + '/lynx-glitches.dat', 'wb').write(dat)
    print('wrote', OUT + '/lynx-glitches.dat')
