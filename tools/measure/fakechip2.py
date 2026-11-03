"""A fake Chip (Chip-type object in slot 1) arrives on / stands on every tile kind except the counted chip,
while the real Chip stands on or slides over various tiles. Lock-step against the original, comparing objects,
map, Chip's inventory (boots, keys, chips left) and the clock every tick."""
import sys, os, random, subprocess, tempfile
sys.path.insert(0, '/home/claude/remake/tools/measure'); sys.path.insert(0, '/home/claude/verify')
import measure as M, cxx_lock as C
TARGETS = {'red key': 0x1E, 'blue key': 0x1F, 'yellow key': 0x20, 'green key': 0x21, 'skates': 0x0F, 'fire boots': 0x10,
    'suction boots': 0x11, 'flippers': 0x12, 'uncounted chip': 0x31, 'exit': 0x25, 'socket': 0x24, 'red door': 0x1A,
    'blue door': 0x1B, 'yellow door': 0x1C, 'green door': 0x1D, 'hint': 0x33, 'thief': 0x15, 'green button': 0x19,
    'blue button': 0x22, 'brown button': 0x2E, 'red button': 0x30, 'teleport': 0x0E, 'trap': 0x2D, 'clone machine': 0x2F,
    'fire': 0x13, 'water': 0x14, 'bomb': 0x2C, 'dirt': 0x03, 'fake blue wall': 0x04, 'real blue wall': 0x32,
    'popup wall': 0x16, 'toggle open': 0x17, 'toggle closed': 0x18, 'hidden wall': 0x26, 'invisible wall': 0x27,
    'gravel': 0x28, 'ice': 0x02, 'ice NW': 0x0A, 'ice NE': 0x0B, 'ice SE': 0x0C, 'ice SW': 0x0D, 'force N': 0x05,
    'force E': 0x06, 'force S': 0x07, 'force W': 0x08, 'force random': 0x09, 'thin E': 0x29, 'thin S': 0x2A, 'thin SE': 0x2B}
CHIPTILE = {'floor': 0x00, 'ice': 0x02, 'force E': 0x06, 'ice corner': 0x0C}
def scenario(rng, tgt, ctile, conveyor=False):
    cells = {(x, y): 0 for x in range(4, 28) for y in range(4, 28)}
    cx, cy = 10, 9
    for x in range(8, 20): cells[(x, cy)] = ctile if ctile != 0x0C else 0x02
    cells[(cx, cy)] = ctile
    sx, sy = 6, 16
    if conveyor:                                           # rides an east force floor into the target
        for x in range(sx, sx + 4): cells[(x, sy)] = 0x06
        cells[(sx + 4, sy)] = tgt
    else: cells[(sx + 1, sy)] = tgt                         # target right next to it: its one step lands there
    if tgt == 0x2E: cells[(14, 22)] = 0x2D                 # brown button -> trap
    if tgt == 0x30: cells[(16, 22)] = 0x2F                 # red button -> clone machine (empty)
    if tgt == 0x0E: cells[(20, 22)] = 0x0E                 # second teleport
    if tgt in (0x19,): cells[(22, 12)] = 0x17; cells[(23, 12)] = 0x18
    objs = [(0x04 | rng.randrange(4), cx, cy), (0x80 | (1 << 2) | M.E, sx, sy)]
    if tgt == 0x22: objs.append((0x80 | (8 << 2) | M.N, 20, 20))   # a tank for the blue button
    inputs = {}
    for _ in range(rng.randrange(0, 3)):
        t0 = rng.randrange(1, 30); d = rng.choice([M.N, M.E, M.S, M.W])
        for t in range(t0, t0 + rng.randrange(1, 6)): inputs[t] = {d}
    boots = {}
    if rng.random() < 0.3: boots = {0x2A + rng.randrange(4): 1}       # the real Chip holds a key
    return M.level(cells, objs), inputs, boots
def lock(data, inputs, boots, T=50):
    R = M.Run(data, boots); r = R.r
    script = ['globals %d %d %d %d %d %d %d' % (r[0x2F], r[0x4A] & 3, 20 - r[0x3BDB], C.joy2bits(r[0x1D48]), C.joy2bits(r[0x1D49]), r[0x29], int(r[0x37] != 0))]
    for a in range(0x0400, 0x0C00):
        if r[a]: script.append('link %x %x' % (a - 0x0400, r[a]))
    for k, v in boots.items(): script.append('poke %x %x' % (k, v))
    emu = []
    for t in range(T):
        jb = 0x01 if t == 0 else 0; bits = 0x10 if t == 0 else 0
        for d in inputs.get(t, ()): jb |= M.JOYB[d]; bits |= C.DBIT[d]
        R.L.joy = jb
        try: ok = R.L.run_to([0x3A11], 4_000_000)
        except RuntimeError: ok = False
        script.append('tick %x' % bits); script.append('dump 20 4'); script.append('dump 26 3'); script.append('dump 2a 4'); script.append('dump 1180 2')
        if not ok: emu.append('crash'); break
        emu.append(C.emu_snap(R) + bytes(r[0x20:0x24]).hex() + bytes(r[0x26:0x29]).hex() + bytes(r[0x2A:0x2E]).hex() + bytes(r[0x1180:0x1182]).hex())
    with tempfile.TemporaryDirectory() as td:
        open(td + '/l.bin', 'wb').write(data); open(td + '/s.txt', 'w').write('\n'.join(script) + '\n')
        out = subprocess.run([C.LP, 'raw', td + '/l.bin', td + '/s.txt'], capture_output=True, text=True, timeout=60).stdout.split('\n')
    rem = []; cur = None; dumps = []
    for l in out:
        if l.startswith('T '):
            if cur is not None: rem.append(cur + ''.join(dumps))
            p = l.split(); cur = 'crash' if p[2] == 'crash' else ''.join(p[3:]); dumps = []
        elif l.startswith('D ') and cur is not None and cur != 'crash': dumps.append(''.join(l.split()[2:]))
    if cur is not None: rem.append(cur + ''.join(dumps))
    n = 0
    for a, b in zip(emu, rem):
        if a != b: break
        n += 1
    return n, emu, rem
def what(a, b):
    if 'crash' in (a, b): return 'crash'
    A, B = bytes.fromhex(a), bytes.fromhex(b)
    if A[:1536] != B[:1536]: return C.describe(a[:3072], b[:3072])
    names = ['skates', 'suction', 'fire', 'flippers', 'chips lo', 'chips hi', 'finished', 'key R', 'key B', 'key Y', 'key G', 'time lo', 'time hi']
    return 'inventory ' + str([(names[i], A[1536 + i], B[1536 + i]) for i in range(13) if A[1536 + i] != B[1536 + i]])
if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3; rng = random.Random(11)
    tot = ok = 0; per = {}; bad = []; unreached = []
    for name, tgt in TARGETS.items():
        for cname, ct in CHIPTILE.items():
            for k in range(n):
                data, inputs, boots = scenario(rng, tgt, ct, conveyor=k % 2 == 1)
                m, emu, rem = lock(data, inputs, boots)
                tx = 10 if k % 2 == 1 else 7
                if emu and all(e != 'crash' for e in emu[:30]) and not any(bytes.fromhex(e)[129] // 8 == tx and bytes.fromhex(e)[257] // 8 == 16 for e in emu): unreached.append((name, k))
                good = m == len(emu) == len(rem)
                tot += 1; ok += good; p = per.setdefault(name, [0, 0]); p[0] += 1; p[1] += good
                if not good: bad.append((name, cname, k, m, what(emu[m], rem[m]) if m < min(len(emu), len(rem)) else 'len %d/%d' % (len(emu), len(rem))))
    print('fake Chip on every other tile: %d scenarios, %d match' % (tot, ok))
    print('  ' + ', '.join('%s %d/%d' % (k, v[1], v[0]) for k, v in per.items() if v[1] < v[0]) or '  all tiles match')
    print('runs where the fake Chip never stood on the target:', len(unreached), unreached[:8])
    for b in bad[:25]: print('DIFF', b)
