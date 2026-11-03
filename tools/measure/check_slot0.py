import sys; sys.path.insert(0,'/home/claude/verify'); import cxx_lock as C, measure as M
fails=[]; ok=0
for t in range(2, 12):
    for code in range(0x34):
        if code in (0x2E, 0x30): continue
        cx, cy = 10, 10
        cells = {(x, y): 0 for x in range(cx - 2, cx + 3) for y in range(cy - 2, cy + 3)}
        cells[(cx, cy)] = code
        if code == 0x0E: cells[(cx - 2, cy)] = 0x0E          # teleport partner
        data = M.level(cells, [(0x80 | (t << 2) | M.S, cx, cy - 1)])
        r = C.run_both(data, {0: {M.N}}, 14)
        if r is None: continue
        n, le, lc, el, cl = r
        if n == le == lc: ok += 1
        else: fails.append((t, code, n, C.describe(el[n], cl[n]) if n < min(le, lc) else 'len %d/%d' % (le, lc)))
print('ok', ok, 'fail', len(fails))
for f in fails: print('type %d code %02X tick %d: %s' % (f[0], f[1], f[2], f[3][:120]))
