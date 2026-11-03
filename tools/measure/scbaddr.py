import sys, json; sys.path.insert(0,'/home/claude/verify'); import measure as M
cx, cy = 15, 15
def ram_after(code, c, r, ticks=1):
    cells = {(cx, cy): 0, (c, r): code, (12, 13): 0}
    objs = [(0x04 | M.N, cx, cy), (0x00 | (8 << 2) | M.N, 12, 13)]
    R = M.Run(M.level(cells, objs))
    ok = True
    for k in range(ticks):
        if not R.tick(M.N if k == 0 else None): ok = False; break
    return ok, bytes(R.L.ram[0:0x10000])
res = {}
for code in list(range(0x34, 0x80)):
    found = []
    for (c, r) in [(17, 13), (12, 18)]:
        ok0, base = ram_after(0x00, c, r)
        ok1, ram = ram_after(code, c, r)
        # where do the tile's screen x (12c-105) and y (12r-105) appear that the control run doesn't have?
        hx, vy = (12 * c - 105) & 0xFF, (12 * r - 105) & 0xFF
        cand = [a for a in range(0x10000 - 2) if ram[a] == hx and ram[a + 2] == vy and not (base[a] == hx and base[a + 2] == vy)]
        found.append((ok1, cand[:6]))
    res['%02X' % code] = found
    print('%02X' % code, found, flush=True)
json.dump(res, open('/tmp/claude-0/scbaddr.json', 'w'))
