"""Code 6E before its crash (doc 04 §4.4): with the damaged byte holding x value V (a value whose crash waits for the
6-tick animation cycle), which addresses receive a tile's screen position, and for which tiles?  Chip parked
mid-map, one probe tile at (17,13) (screen x 99, y 51), the damage put in place directly after tick 0."""
import sys; sys.path.insert(0, '/home/claude/verify'); import measure as M
sys.path.insert(0, '/home/claude/remake/tools/measure'); from pokedelay import run as delay
def probe(tile, v, ticks=5, cell=(17, 13), y=75):
    cells = {(x, yy): 0 for x in range(32) for yy in range(32)}; cells[cell] = tile
    R = M.Run(M.level(cells, [(0x04 | M.N, 15, 15)]))
    R.tick(None)
    for i, b in enumerate((v, 0, y, 0)): R.L.ram[0x2F00 + i] = b
    hx, vy = 12 * cell[0] - 105, 12 * cell[1] - 105
    found = {}
    for k in range(1, ticks):
        base = bytes(R.L.ram[0:0x4000])
        if not R.tick(None): found['crash'] = k; break
        ram = bytes(R.L.ram[0:0x4000])
        for a in range(0x4000 - 2):
            if ram[a] == hx and ram[a + 2] == vy and (base[a], base[a + 2]) != (hx, vy) and a not in found:
                found[a] = k
    return found
if __name__ == '__main__':
    six = [v for v in range(6, 136) if delay(0x2F00, [v, 0, 75, 0]) == 6]
    print('class-6 values in 6..135:', len(six), six[:20])
    for tile in [0x00, 0x01, 0x25, 0x14, 0x13, 0x0E, 0x17, 0x18, 0x09, 0x05, 0x23]:
        r = probe(tile, six[0])
        print('tile %02X v=%d:' % (tile, six[0]), {('%04X' % a if a != 'crash' else a): k for a, k in r.items()})

def table(cells=((17, 13), (12, 17))):
    six = [v for v in range(6, 136) if delay(0x2F00, [v, 0, 75, 0]) == 6]
    out = {}
    for v in six:
        for tile in (0x25, 0x14, 0x13, 0x0E):
            rs = [probe(tile, v, ticks=6, cell=c) for c in cells]
            addrs = [sorted((a, k) for a, k in r.items() if a != 'crash') for r in rs]
            out[(v, tile)] = addrs
    return six, out
