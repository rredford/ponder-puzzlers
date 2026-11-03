"""Where does drawing an object in state S write its screen position?  (doc 04 §4.4; the object counterpart of
scbaddr.py.)  One object in slot 5 at (17,13) (screen x 99, y 51), Chip parked at (15,15); states with bit 7 set
take no part in the game logic, so only their drawing acts."""
import sys, json; sys.path.insert(0, '/home/claude/verify'); import measure as M
def addrs(s, cell=(17, 13), ticks=2):
    cells = {(x, y): 0 for x in range(32) for y in range(32)}
    objs = [(0x04 | M.N, 15, 15)] + [(0, 0, 0)] * 4 + [(s, *cell)]
    R = M.Run(M.level(cells, objs))
    ok = True
    for k in range(ticks):
        if not R.tick(None): ok = False; break
    ram = bytes(R.L.ram[0:0x10000])
    hx, vy = 12 * cell[0] - 105, 12 * cell[1] - 105
    return ok, [a for a in range(0x10000 - 2) if ram[a] == hx and ram[a + 2] == vy]
if __name__ == '__main__':
    _, base = addrs(0x00)
    res = {}
    for s in range(0x80, 0x100):
        ok, a = addrs(s)
        a = [x for x in a if x not in base]
        res['%02X' % s] = (ok, a)
    json.dump(res, open('/tmp/claude-0/objaddr.json', 'w'))
    for s, (ok, a) in res.items(): print(s, 'ok' if ok else 'CRASH', ' '.join('%04X' % x for x in a[:4]))
