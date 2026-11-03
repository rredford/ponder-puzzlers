"""Survival play for sets without solutions (e.g. CC1telewalls): each tick Chip, when on a cell, picks a random
direction whose target cell is not next to a monster (keeps it for one cell), else waits. Inputs are decided from the
original's own state, recorded, and replayed into the remake in lock-step.  usage: survive.py LXDIR FROM TO [TICKS]"""
import sys, os, random, subprocess, tempfile
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
D = [(M.N, 0, -1), (M.E, 1, 0), (M.S, 0, 1), (M.W, -1, 0)]
def play(data, seed, T=600):
    R = M.Run(data)
    if not R.ok: return None
    r = R.r; rng = random.Random(seed)
    script = ['globals %d %d %d %d %d %d %d' % (r[0x2F], r[0x4A] & 3, 20 - r[0x3BDB], C.joy2bits(r[0x1D48]), C.joy2bits(r[0x1D49]), r[0x29], int(r[0x37] != 0))]
    for a in range(0x0400, 0x0C00):
        if r[a]: script.append('link %x %x' % (a - 0x0400, r[a]))
    emu = []; cur = None; outcome = 'alive'
    for t in range(T):
        x, y = r[0x1080], r[0x1100]
        if x % 8 == 0 and y % 8 == 0:
            cx, cy = x // 8, y // 8
            mons = [(r[0x1080 + i] // 8, r[0x1100 + i] // 8) for i in range(1, 128)
                    if r[0x1000 + i] and not r[0x1000 + i] & 0x40 and ((r[0x1000 + i] >> 2) & 15) not in (7, 0)]
            safe = [d for d in D if all(abs(cx + d[1] - mx) + abs(cy + d[2] - my) > 1 for mx, my in mons)]
            cur = rng.choice(safe)[0] if safe and rng.random() < 0.85 else None
        jb = 0x01 if t == 0 else 0; bits = 0x10 if t == 0 else 0
        if cur is not None: jb |= M.JOYB[cur]; bits |= C.DBIT[cur]
        R.L.joy = jb
        try: ok = R.L.run_to([0x3A11], 4_000_000)
        except RuntimeError: ok = False
        script.append('tick %x' % bits)
        if not ok: emu.append('crash'); outcome = 'crash'; break
        emu.append(C.emu_snap(R))
        if r[0x28]: outcome = 'win'; break
        if r[0x24]: outcome = 'death'; break
    with tempfile.TemporaryDirectory() as td:
        open(td + '/l.bin', 'wb').write(data); open(td + '/s.txt', 'w').write('\n'.join(script) + '\n')
        out = subprocess.run([C.LP, 'raw', td + '/l.bin', td + '/s.txt'], capture_output=True, text=True, timeout=120).stdout.split('\n')
    rem = ['crash' if l.split()[2] == 'crash' else ''.join(l.split()[3:]) for l in out if l.startswith('T ')]
    flag = next((l for l in out if 'outofsync' in l), None)
    n = 0
    for a, b in zip(emu, rem):
        if a != b: break
        n += 1
    return outcome, len(emu), n, len(rem), flag, (C.describe(emu[n], rem[n]) if n < min(len(emu), len(rem)) else '')
if __name__ == '__main__':
    d, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); T = int(sys.argv[4]) if len(sys.argv) > 4 else 600
    for lv in range(lo, hi + 1):
        try: data = open('%s/%d.bin' % (d, lv), 'rb').read()
        except FileNotFoundError: continue
        for seed in (1, 2):
            res = play(data, lv * 10 + seed, T)
            if res is None: print(lv, seed, 'level does not start (hangs at load)', flush=True); continue
            o, le, m, lc, flag, desc = res
            print(lv, seed, o, 'ticks', le, 'in sync' if m == le == lc else 'DIFF at %d (%s)%s' % (m, desc, ' notice: ' + flag if flag else ''), flush=True)
