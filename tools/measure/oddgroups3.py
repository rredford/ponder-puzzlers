"""Oddity 2, grouped sweep, step 3: event course.  Chip walks east over chip, key, door, skates, blue
button, green button, hint, block push, then exit (course X) or water (course W); an odd code stays in
view.  Reports the tick the original crashes (or '.' if it survives to the level end / death screen)."""
import sys, json; sys.path.insert(0, '/home/claude/verify'); import measure as M
def course(code, end, T=90, at=(17, 13)):
    cells = {(x, y): 0 for x in range(8, 26) for y in range(11, 19)}
    for x, t in zip(range(10, 22), [0x23, 0x1E, 0x0F, 0x22, 0x19, 0x33, 0, 0, 0, 0, 0, end]): cells[(x, 15)] = t
    cells[(22, 15)] = 1; cells[(12, 18)] = 1
    cells[(18, 17)] = 0x17; cells[(19, 17)] = 0x18   # toggle walls
    if code is not None: cells[at] = code
    objs = [(0x04 | M.E, 9, 15), (0x80 | (8 << 2) | M.S, 12, 17)]  # block, tank
    R = M.Run(M.level(cells, objs))
    for k in range(T):
        if not R.tick(M.E if k < 60 else None): return k, R.r[0x1080], R.r[0x28], R.r[0x1000]
    return None, R.r[0x1080], R.r[0x28], R.r[0x1000]
if __name__ == '__main__':
    base = {e: course(None, e) for e in (0x25, 0x14)}
    print('control', base)
    for cs in sys.argv[1:]:
        r = [course(int(cs, 16), e) for e in (0x25, 0x14)]
        print(cs, ' '.join(('same' if x == base[e] else str(x)) for x, e in zip(r, (0x25, 0x14))), flush=True)
