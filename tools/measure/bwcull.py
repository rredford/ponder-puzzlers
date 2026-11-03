"""Test-only interventions on Lynx-ruleset solutions (current replay protocol: A on tick 0, slide -> R):
  nobw  - blobs and walkers removed from the level (deterministic monsters only)
  cull  - before every tick, any monster standing on an edge cell facing out of the map is removed
  both  - both
Replayed on the original (emulated); a win is then checked in lock-step against the remake (same removals fed to
it as memory writes).  usage: bwcull.py SET [SET ...]"""
import sys, os, json, subprocess, tempfile, collections
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify'); sys.path.insert(0, '/tmp/claude-0/edgeprot')
import measure as M, cxx_lock as C, tws, inject_run as I, run as P
SL = (0, 3, 2, 1)
OUT = {0: lambda x, y: y == 0, 1: lambda x, y: x == 31, 2: lambda x, y: y == 31, 3: lambda x, y: x == 0}
def strip_bw(data):
    d = bytearray(data); n = 0
    for i in range(1, 128):
        st = d[0x400 + i]
        if st and not st & 0x40 and ((st >> 2) & 15) in (9, 10): d[0x400 + i] = 0; n += 1
    return bytes(d), n
def moves_of(rec):
    mv = {}
    for t, d in rec['moves']: mv.setdefault(t, set()).update(I.TWDIR[d])
    return mv
def replay(data, rec, cull, extra=400):
    R = M.Run(data)
    if not R.ok: return 'no-start', None, {}
    r = R.r; r[0x4A] = (r[0x4A] & ~3) | SL[rec['slide'] & 3]
    mv = moves_of(rec); pokes = {}
    for t in range(rec['moves'][-1][0] + extra):
        if cull:
            for i in range(1, 128):
                st = r[0x1000 + i]
                if not st or st & 0x40: continue
                x, y = r[0x1080 + i], r[0x1100 + i]
                if x % 8 or y % 8: continue
                cx, cy = x // 8, y // 8
                if OUT[st & 3](cx, cy):
                    c = cy * 32 + cx; pk = pokes.setdefault(t, [])
                    if r[0x0C00 + c] == (0x80 | i): r[0x0C00 + c] = r[0x1200 + i]; pk.append((0x0C00 + c, r[0x1200 + i]))
                    r[0x1000 + i] = 0; pk.append((0x1000 + i, 0))
        jb = 0x01 if t == 0 else 0
        for d in mv.get(t, ()): jb |= M.JOYB[d]
        R.L.joy = jb
        try: ok = R.L.run_to([0x3A11], 4_000_000)
        except RuntimeError: ok = False
        if not ok: return 'crash', t, pokes
        if r[0x28]: return 'win', t, pokes
        if r[0x24]: return 'death', t, pokes
    return 'stall', None, pokes
def lockstep(data, rec, pokes, T):
    R = M.Run(data); r = R.r; r[0x4A] = (r[0x4A] & ~3) | SL[rec['slide'] & 3]
    script = ['globals %d %d %d %d %d %d %d' % (r[0x2F], r[0x4A] & 3, 20 - r[0x3BDB], C.joy2bits(r[0x1D48]), C.joy2bits(r[0x1D49]), r[0x29], int(r[0x37] != 0))]
    for a in range(0x0400, 0x0C00):
        if r[a]: script.append('link %x %x' % (a - 0x0400, r[a]))
    mv = moves_of(rec); elog = []
    for k in range(T):
        for a, v in pokes.get(k, ()): r[a] = v; script.append('poke %x %x' % (a, v))
        jb = 0x01 if k == 0 else 0; bits = 0x10 if k == 0 else 0
        for d in mv.get(k, ()): jb |= M.JOYB[d]; bits |= C.DBIT[d]
        R.L.joy = jb
        try: ok = R.L.run_to([0x3A11], 4_000_000)
        except RuntimeError: ok = False
        script.append('tick %x' % bits)
        if not ok: elog.append('crash'); break
        elog.append(C.emu_snap(R))
    with tempfile.TemporaryDirectory() as td:
        open(td + '/l.bin', 'wb').write(data); open(td + '/s.txt', 'w').write('\n'.join(script) + '\n')
        out = subprocess.run([C.LP, 'raw', td + '/l.bin', td + '/s.txt'], capture_output=True, text=True, timeout=600).stdout.split('\n')
    clog = ['crash' if l.split()[2] == 'crash' else ''.join(l.split()[3:]) for l in out if l.startswith('T ')]
    n = 0
    for a, b in zip(elog, clog):
        if a != b: break
        n += 1
    return n == len(elog) == len(clog)
if __name__ == '__main__':
    out = {}
    for name in sys.argv[1:]:
        tf, bd, of, lynx = P.SETS[name]
        orc = {}
        for l in open('/home/claude/remake/tests/' + of):
            if l.startswith('#') or not l.strip(): continue
            p = l.rstrip('\n').split('\t'); orc[int(p[0])] = p[2]
        recs = {r['level']: r for r in tws.parse(tf)['recs'] if r.get('moves')}
        for lv in sorted(recs):
            if lv not in orc or orc[lv] == 'win': continue
            raw = open('%s/%d.bin' % (bd, lv), 'rb').read(); nobw, nbw = strip_bw(raw)
            variants = []
            if nbw: variants.append(('nobw', nobw, False))
            if orc[lv] == 'crash': variants.append(('cull', raw, True))
            if nbw and orc[lv] == 'crash': variants.append(('both', nobw, True))
            for vn, data, cull in variants:
                o, t, pk = replay(data, recs[lv], cull)
                sync = lockstep(data, recs[lv], pk, t + 1) if o == 'win' else None
                print(name, lv, 'was', orc[lv], '|', vn, '->', o, t, '| blobs/walkers removed %d' % nbw if 'bw' in vn or vn == 'both' else '', '| remake in sync' if sync else ('| REMAKE DIFFERS' if sync is False else ''), flush=True)
                out.setdefault(vn, collections.Counter())[o] += 1
    for k, v in out.items(): print(k, dict(v))
