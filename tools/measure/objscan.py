"""Which cells does the original's object pass visit (doc 04 §4.4, row table)?  Parked tanks fill a block of
cells; one row-table entry (0x2F53 + row) is set; sprite-memory writes are logged (the write-logging emulator
build, awlog mode 4) and each object's screen-position write at 4D19 is mapped back to its cell, in order.
Result: only the window's last row goes through the lookup; the pass visits base - 32*(10-m) + k (m, k = 0..10),
base = 256*(row/8) + T[row] + c0, in reading order (64256/64256 cells over all 256 values).
usage: objscan.py A|B   (rows 8..15 or 16..23, columns 6..21; Chip parked at (15,15))"""
import sys, ctypes, json
sys.path.insert(0, '/tmp/claude-0'); sys.path.insert(0, '/home/claude/verify')
import clynxt4; from clynxt4 import CLynx, lib
lib.get_aw_a.argtypes = [ctypes.c_int]; lib.get_aw_v.argtypes = [ctypes.c_int]; lib.set_awlog.argtypes = [ctypes.c_int]
import inject_run; inject_run.lib = lib
from inject_run import inject
import measure as M
def found(entries, rows, cols):
    objs = [(0x04 | M.N, 15, 15)]
    for y in rows:
        for x in cols:
            if (x, y) != (15, 15) and len(objs) < 128: objs.append((0x20 | M.N, x, y))
    L = CLynx('/home/claude/rom/st_i.pkl'); inject(L, M.level({(x, y): 0 for x in range(32) for y in range(32)}, objs))
    L.ram[0x0A] = 0; L.ram[0x3E] = 1; L.ram[0x39] = 10; L.joy = 0
    assert L.run_to([0x39DF], 4_000_000) and L.run_to([0x3A11], 4_000_000)
    for j, v in entries.items(): L.ram[0x2F53 + j] = v
    lib.set_awlog(4); L.run_to([0x3A11], 4_000_000)
    w = [(lib.get_aw_a(j), lib.get_aw_v(j)) for j in range(lib.get_aw_n())]; lib.set_awlog(0)
    r = L.ram; cx = min(max(r[0x1080] // 2 - 16, 0), 93); cy = min(max(r[0x1100] // 2 - 16, 0), 93)
    pos = {((3 * (x * 4 - cx) + 27) & 0xFFFF, (3 * (y * 4 - cy) + 27) & 0xFFFF): (x, y) for s, x, y in objs[1:]}
    seq = []
    for i in range(len(w) - 3):
        if [w[i + k][0] for k in range(4)] == [0x4D19, 0x4D1A, 0x4D1B, 0x4D1C]:
            p = (w[i][1] | w[i + 1][1] << 8, w[i + 2][1] | w[i + 3][1] << 8); seq.append(pos.get(p, p))
    return seq
if __name__ == '__main__':
    rows = range(8, 16) if sys.argv[1] == 'A' else range(16, 24)
    print(json.dumps({v: found({20: v}, rows, range(6, 22)) for v in range(256)}))
