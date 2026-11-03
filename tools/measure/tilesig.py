import sys, json; sys.path.insert(0,'/home/claude/verify'); import measure as M, cxx_lock as C
lo, hi, out = int(sys.argv[1], 16), int(sys.argv[2], 16), sys.argv[3]
cx, cy = 15, 15                      # Chip sealed; camera window cols/rows 10..20
res = {}
for code in range(lo, hi):
    grid = []
    for r in range(10, 21):
        row = ''
        for c in range(10, 21):
            if (c, r) == (cx, cy): row += 'C'; continue
            cells = {(cx, cy): 0, (c, r): code, (12, 13) if (c, r) != (12, 13) else (12, 17): 0}
            for x in range(2, 30): cells[(x, 5)] = 0          # monster corridor (out of view)
            park = (12, 13) if (c, r) != (12, 13) else (12, 17)
            objs = [(0x04 | M.N, cx, cy), (0x80 | (4 << 2) | M.E, 3, 5), (0x00 | (8 << 2) | M.N, *park)]
            n, le, lc, el, cl = C.run_both(M.level(cells, objs), {0: {M.N}}, 8)
            if n == le == lc: row += '.'
            elif el[-1] == 'crash' and n == le - 1: row += str(min(9, n))     # crash on tick n
            else: row += 'w'                                                 # memory differs (no crash yet)
        grid.append(row)
    res['%02X' % code] = grid
    json.dump(res, open(out, 'w'))
