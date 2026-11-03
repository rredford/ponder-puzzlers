"""Lock-step the C++ engine (levelpack raw) against the emulated original on small test levels."""
import sys, subprocess, tempfile, os
sys.path.insert(0, '/home/claude/verify')
import measure as M
from lockstep import JOY
import doc_engine as DE
LP = '/home/claude/remake/build/levelpack'
DBIT = {M.N: 1, M.E: 2, M.S: 4, M.W: 8}
def joy2bits(b): return sum(DBIT[d] for d in range(4) if b & M.JOYB[d])

def emu_snap(R):
    r = R.r
    return (bytes(r[0x1000:0x1080]) + bytes(r[0x1080:0x1100]) + bytes(r[0x1100:0x1180]) + bytes(r[0x1200:0x1280]) +
            bytes(r[0x0C00:0x1000])).hex()

def run_both(data, inputs, ticks, pokes=(), boots=None, nodraw=False, start=False, rf=None):
    """inputs: {tick: set of dirs}; pokes: [(addr, val)] applied right after the level starts.
    start=True presses the A button on tick 0, which starts the level (and its monsters) without moving Chip:
    otherwise nothing moves until Chip's first input."""
    start = start or os.environ.get('CC_START') == '1'   # rerun any existing test with the A-button start
    R = M.Run(data, boots)
    if not R.ok: return None
    r = R.r
    if rf is not None: r[0x4A] = (r[0x4A] & ~3) | rf
    script = ['globals %d %d %d %d %d %d %d' % (r[0x2F], r[0x4A] & 3, 20 - r[0x3BDB], joy2bits(r[0x1D48]), joy2bits(r[0x1D49]), r[0x29], int(r[0x37] != 0))]
    for a in range(0x0400, 0x0C00):
        if r[a]: script.append('link %x %x' % (a - 0x0400, r[a]))
    for k, v in (boots or {}).items(): script.append('poke %x %x' % (k, v))
    for a, v in pokes:
        r[a] = v; script.append('poke %x %x' % (a, v))
    if nodraw: script.append('nodraw')
    elog = []
    for k in range(ticks):
        jb = 0; bits = 0
        for d in inputs.get(k, ()): jb |= M.JOYB[d]; bits |= DBIT[d]
        if start and k == 0: jb |= 0x01; bits |= 0x10
        R.L.joy = jb
        try: ok = R.L.run_to([0x3A11], 4_000_000)
        except RuntimeError: ok = False
        if not ok: elog.append('crash'); break
        elog.append(emu_snap(R))
        script.append('tick %x' % bits)
    else: pass
    if elog and elog[-1] == 'crash':
        k = len(elog) - 1
        script.append('tick %x' % (sum(DBIT[d] for d in inputs.get(k, ())) | (0x10 if start and k == 0 else 0)))
    with tempfile.TemporaryDirectory() as td:
        open(td + '/l.bin', 'wb').write(data); open(td + '/s.txt', 'w').write('\n'.join(script) + '\n')
        try: out = subprocess.run([LP, "raw", td + "/l.bin", td + "/s.txt"], capture_output=True, text=True, timeout=20).stdout.split("\n")
        except subprocess.TimeoutExpired: out = ["T 0 HANG"]
    clog = []
    run_both.outofsync = None
    for line in out:
        if line.startswith('F ') and 'outofsync' in line: run_both.outofsync = int(line.split()[1])
        if not line.startswith('T '): continue
        p = line.split()
        clog.append('crash' if p[2] == 'crash' else ''.join(p[3:]))
    n = 0
    for a, b in zip(elog, clog):
        if a != b: break
        n += 1
    return n, len(elog), len(clog), elog, clog

def describe(a, b):
    if a == 'crash' or b == 'crash': return 'emu %s / c++ %s' % ('crash' if a == 'crash' else 'ok', 'crash' if b == 'crash' else 'ok')
    A = bytes.fromhex(a); B = bytes.fromhex(b)
    names = [('state', 0, 128), ('x', 128, 128), ('y', 256, 128), ('under', 384, 128), ('map', 512, 1024)]
    out = []
    for nm, o, n in names:
        d = [(i, A[o + i], B[o + i]) for i in range(n) if A[o + i] != B[o + i]]
        if d: out.append('%s %s' % (nm, [(i, hex(x), hex(y)) for i, x, y in d[:4]]))
    return '; '.join(out)
