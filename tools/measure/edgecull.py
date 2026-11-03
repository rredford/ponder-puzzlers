"""Test-only intervention: replay a solution on the original (emulated) with the map edge as it is, but before
every tick remove any monster that stands on an edge cell facing out of the map (it would walk off the map this
tick).  The same removals are fed to the remake as memory writes, so both can be lock-stepped.
run(rec, data) -> (outcome, tick, removals, crossings_left, script_pokes)"""
import sys; sys.path.insert(0, '/home/claude/verify')
import emu_only as E
from inject_run import inject
from clynx import CLynx
from lockstep import JOY
OUT = {0: lambda x, y: y == 0, 1: lambda x, y: x == 31, 2: lambda x, y: y == 31, 3: lambda x, y: x == 0}
def wrapped(a, b): return (a < 8 and b >= 240) or (a >= 240 and b < 8)
def run(rec, data, extra=400):
    L = CLynx('/home/claude/rom/st_i.pkl'); inject(L, data)
    L.ram[0x0A] = 0; L.ram[0x3E] = 1; L.ram[0x39] = 10; L.joy = 0
    if not (L.run_to([0x39DF]) and L.run_to([0x3A11])): return 'crash', 0, 0, 0, {}
    moves = {}
    for t, d in rec['moves']: moves[t] = moves.get(t, set()) | E.dirs(d)
    removed = 0; crossings = 0; pokes = {}
    r = L.ram
    for t in range(rec['moves'][-1][0] + extra):
        for i in range(1, 128):
            st = r[0x1000 + i]
            if not st or st & 0x40: continue
            x, y = r[0x1080 + i], r[0x1100 + i]
            if x % 8 or y % 8: continue
            cx, cy = x // 8, y // 8
            if OUT[st & 3](cx, cy):
                c = cy * 32 + cx
                pk = pokes.setdefault(t, [])
                if r[0x0C00 + c] == (0x80 | i):
                    r[0x0C00 + c] = r[0x1200 + i]; pk.append((0x0C00 + c, r[0x1200 + i]))
                r[0x1000 + i] = 0; pk.append((0x1000 + i, 0)); removed += 1
        prev = [(r[0x1000 + i], r[0x1080 + i], r[0x1100 + i]) for i in range(128)]
        jb = 0
        for d in moves.get(t, ()): jb |= JOY[E.DM[d]]
        L.joy = jb
        try: ok = L.run_to([0x3A11])
        except RuntimeError: ok = False
        if not ok: return 'crash', t, removed, crossings, pokes
        for i in range(128):
            if r[0x1000 + i] and prev[i][0] and (wrapped(prev[i][1], r[0x1080 + i]) or wrapped(prev[i][2], r[0x1100 + i])): crossings += 1
        if r[0x28]: return 'win', t, removed, crossings, pokes
        if r[0x24]: return 'death', t, removed, crossings, pokes
    return 'stall', None, removed, crossings, pokes
def lockstep(rec, data, pokes, T):
    """the remake with the same removals, compared tick for tick with the original"""
    import cxx_lock as C, subprocess, tempfile
    import measure as M
    R = M.Run(data); r = R.r
    script = ['globals %d %d %d %d %d %d' % (r[0x2F], r[0x4A] & 3, 20 - r[0x3BDB], C.joy2bits(r[0x1D48]), C.joy2bits(r[0x1D49]), r[0x29])]
    for a in range(0x0400, 0x0C00):
        if r[a]: script.append('link %x %x' % (a - 0x0400, r[a]))
    moves = {}
    for t, d in rec['moves']: moves.setdefault(t, set()).update(E.DM[x] for x in E.dirs(d))
    elog = []
    for k in range(T):
        for a, v in pokes.get(k, ()): r[a] = v; script.append('poke %x %x' % (a, v))
        jb = 0; bits = 0
        for d in moves.get(k, ()): jb |= M.JOYB[d]; bits |= C.DBIT[d]
        R.L.joy = jb
        try: ok = R.L.run_to([0x3A11], 4_000_000)
        except RuntimeError: ok = False
        script.append('tick %x' % bits)
        if not ok: elog.append('crash'); break
        elog.append(C.emu_snap(R))
    with tempfile.TemporaryDirectory() as td:
        open(td + '/l.bin', 'wb').write(data); open(td + '/s.txt', 'w').write('\n'.join(script) + '\n')
        out = subprocess.run([C.LP, 'raw', td + '/l.bin', td + '/s.txt'], capture_output=True, text=True, timeout=60).stdout.split('\n')
    clog = ['crash' if l.split()[2] == 'crash' else ''.join(l.split()[3:]) for l in out if l.startswith('T ')]
    n = 0
    for a, b in zip(elog, clog):
        if a != b: break
        n += 1
    return n, len(elog), len(clog)
