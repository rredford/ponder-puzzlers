"""When does the original stop drawing objects after the cell lookup's row table is changed (doc 04 §4.4)?
Open map, Chip parked, one parked tank in view; one row-table entry (0x2F53 + row) is set to a value, and we
check every tick whether the tank's screen position is still written into the sprite area."""
import sys; sys.path.insert(0, '/home/claude/verify'); import measure as M
def drawn_seq(row, val, chip=(15, 15), mon=(17, 13), T=4, idle=True):
    cells = {(x, y): 0 for x in range(32) for y in range(32)}
    R = M.Run(M.level(cells, [(0x04 | M.N, *chip), (0x00 | (8 << 2) | M.N, *mon)]))
    R.L.ram[0x2F53 + row] = val
    out = ''
    for k in range(T):
        for a in range(0x4900, 0x5300): R.L.ram[a] = 0xEE if 0 else R.L.ram[a]
        b = bytes(R.L.ram[0x4900:0x5300])
        if not R.tick(None): return out + 'X'
        a = bytes(R.L.ram[0x4900:0x5300])
        qx, qy = R.r[0x1080] // 2, R.r[0x1100] // 2; cx = min(max(qx - 16, 0), 93); cy = min(max(qy - 16, 0), 93)
        px = 3 * (R.r[0x1081] // 2 - cx) + 27; py = 3 * (R.r[0x1101] // 2 - cy) + 27
        out += 'y' if any(a[x] == px and a[x + 2] == py for x in range(len(a) - 2)) else '-'
    return out
