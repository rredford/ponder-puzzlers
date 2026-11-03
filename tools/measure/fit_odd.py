"""Fit a behaviour model to the tile codes past the real tile set on which an arriving object does NOT crash
the original.  Model per code: measured entry table, slide and ice flags, plus a leave mask and a handler
that behaves like the handler of a real tile K.  Each candidate is scored by lock-step against the emulated
original in open-room scenarios.

usage: python3 fit_odd.py CODE [CODE...]
"""
import sys, json, itertools
sys.setrecursionlimit(400)
sys.path.insert(0, '/home/claude/verify')
import measure as M
import doc_engine as DE
from lockstep import JOY
SP = '/tmp/claude-0/-home-claude/4a4b5c09-bdf2-5f61-92c2-02c1c6ac6cfd/scratchpad/'
TAB = json.load(open(SP + 'table_ab.json'))
SLIDE = {int(c) for c, v in TAB['slide'].items() if v == [True]}
ICE = set(json.load(open(SP + 'ice.json'))) if False else None

class Crash(Exception): pass

class OddGame(DE.Game):
    MODEL = {}          # code -> dict(leave, flags, alias, crash_arrive:set of (who, dir))
    def test_move(s, i):
        if s.dying(i): return False
        d = s.dir(i)
        u = s.under[i]
        if u >= 0x34 and u < 0x80:
            if s.MODEL[u]['leave'] & DE.DIRBIT[d]: return False
        elif s.T[u][1] & DE.DIRBIT[d]: return False
        t = s.neighbour(s.cell(i), d)
        v = s.map[t]
        if 0x34 <= v < 0x80:
            return bool(TAB['enter'][str(v)][s.typ(i) - 1][d])
        if v >= 0x80:
            j = v & 0x7F
            if 0x34 <= s.under[j] < 0x80:
                if not TAB['enter'][str(s.under[j])][s.typ(i) - 1][d]: return False
                # fall through to object rules with entry allowed
                save = s.under[j]; s.under[j] = 0
                try: return DE.Game.test_move(s, i)
                finally:
                    if s.under[j] == 0: s.under[j] = save
        return DE.Game.test_move(s, i)
    def handler(s, i, ev):
        u = s.under[i]
        if 0x34 <= u < 0x80:
            m = s.MODEL[u]
            who = 'chip' if i == 0 else 'mon'
            if ev == DE.ARRIVE and (who, s.dir(i)) in m['crash_arrive']: raise Crash()
            if m['alias'] == 'crash': raise Crash()
            if isinstance(m['alias'], tuple):                     # ('adv', {dir: newdir}): turn and move on at once
                if ev != DE.ARRIVE: raise Crash()                # blocked while standing on it
                nd = m['alias'][1].get(s.dir(i))
                if nd is None: raise Crash()
                s.setdir(i, nd, True); s.advance(i); return
            s.under[i] = m['alias']
            try: DE.Game.handler(s, i, ev)
            finally:
                if s.under[i] == m['alias']: s.under[i] = u
            return
        DE.Game.handler(s, i, ev)

def flags_of(code, ice):
    return (DE.SLIDE if code in SLIDE else 0) | (DE.ICE if ice else 0)

_T_patch = {}
def run_doc(data, L0, inputs, ticks, model, code, ice):
    OddGame.MODEL = {code: model}
    G = OddGame(list(data), tick=L0['tick'], R=L0['R'], row_above=L0['row_above']); G.sub = L0['sub']
    G.T[code] = [0, 0, flags_of(code, ice)]          # flags only (leave/entry handled by the model)
    log = []
    for k in range(ticks):
        try: G.tick_once(set(inputs.get(k, ())))
        except (Crash, KeyError, RecursionError): log.append("crash"); break
        log.append(snap_doc(G))
    return log

def snap_doc(G):
    return (tuple(G.state[:4]), tuple(G.x[:4]), tuple(G.y[:4]), tuple(G.under[:4]), tuple(G.map[:1024]))
def snap_emu(R):
    r = R.r
    return (tuple(r[0x1000:0x1004]), tuple(r[0x1080:0x1084]), tuple(r[0x1100:0x1104]), tuple(r[0x1200:0x1204]),
            tuple(r[0x0C00:0x1000]))

def scenario(code, mover, d, extra):
    """returns (level data, initial globals, inputs dict) - same layout as measure.room_run"""
    cx, cy = (8, 8) if mover != 1 else (26, 26)
    cells = {(x, y): 0 for x in range(cx - 2, cx + 3) for y in range(cy - 2, cy + 3)}
    cells[(cx, cy)] = code
    sx, sy = cx - M.DX[d], cy - M.DY[d]
    if mover == 1: objs = [(0x04 | d, sx, sy)]
    else: cells[M.CHIP] = 0; objs = [(0x04 | M.N, *M.CHIP), (0x80 | (mover << 2) | d, sx, sy)]
    inputs = {0: {d if mover == 1 else M.N}}
    for k, e in extra: inputs[k] = {e}
    return M.level(cells, objs), inputs

def run_emu(data, inputs, ticks):
    R = M.Run(data)
    L0 = dict(tick=R.r[0x2F], R=R.r[0x4A] & 3, row_above=list(R.r[0x0BE0:0x0C00]), sub=20 - R.r[0x3BDB])
    log = []
    for k in range(ticks):
        dirs = inputs.get(k, ())
        R.L.joy = 0
        jb = 0
        for e in dirs: jb |= M.JOYB[e]
        R.L.joy = jb
        try: ok = R.L.run_to([0x3A11], 4_000_000)
        except RuntimeError: ok = False
        if not ok: log.append('crash'); break
        log.append(snap_emu(R))
    return log, L0

ALIASES = [0x00, 0x02, 0x03, 0x05, 0x06, 0x07, 0x08, 0x0A, 0x0B, 0x0C, 0x0D, 0x0F, 0x15, 0x16, 0x23, 0x25, 0x2D, 0x2F, 'crash']

def fit(code, ticks=16, aliases=None):
    sc = []
    for who in (1, 2, 7, 4):
        for d in range(4):
            if not TAB['enter'][str(code)][who - 1][d]: continue
            for extra in ([], [(8, 0)], [(8, 1)], [(8, 2)], [(8, 3)]) if who == 1 else ([],):
                data, inputs = scenario(code, who, d, extra)
                elog, L0 = run_emu(data, inputs, ticks)
                sc.append((who, d, extra, data, inputs, L0, elog))
    if not sc: return None
    # crash-on-arrival set straight from observation (arrival.json)
    arr = json.load(open(SP + 'arrival.json')).get(str(code), {})
    crash_arrive = {(k[:-1], int(k[-1])) for k, v in arr.items() if v.startswith('crash')}
    best = []
    for alias in (aliases or ALIASES):
        for leave in range(16):
            for ice in (False, True):
                model = dict(leave=leave, alias=alias, crash_arrive=crash_arrive)
                score = 0
                for who, d, extra, data, inputs, L0, elog in sc:
                    dlog = run_doc(data, L0, inputs, ticks, model, code, ice)
                    n = 0
                    for a, b in zip(elog, dlog):
                        if a != b: break
                        n += 1
                    if len(elog) == len(dlog) and n == len(elog): n += 1
                    score += n
                best.append((score, alias, leave, ice))
    best.sort(key=lambda r: -r[0])
    full = sum(len(s[-1]) + 1 for s in sc)
    return full, best[:5], len(sc)

EXTRA = {0x4A: [('adv', {0: 2, 1: 1, 2: 2, 3: 1})], 0x43: [('adv', {2: 2, 3: 3})], 0x71: [('adv', {0: 0, 1: 1, 2: 0, 3: 3})]}
if __name__ == '__main__':
    out = {}
    for c in sys.argv[1:]:
        code = int(c, 16)
        r = fit(code, aliases=EXTRA.get(code))
        print('%02X' % code, r, flush=True)
        out[code] = r

def tiebreak(code, cands, ticks=16):
    """Score candidate models on Chip-with-skates / suction scenarios (Chip can steer on ice with skates)."""
    sc = []
    for boots in ({0x20: 1}, {0x21: 1}, {0x22: 1}):
        for d in range(4):
            if not TAB['enter'][str(code)][0][d]: continue
            for extra in ([], [(5, 0)], [(5, 1)], [(5, 2)], [(5, 3)]):
                data, inputs = scenario(code, 1, d, extra)
                R = M.Run(data, boots)
                L0 = dict(tick=R.r[0x2F], R=R.r[0x4A] & 3, row_above=list(R.r[0x0BE0:0x0C00]), sub=20 - R.r[0x3BDB])
                el = []
                for k in range(ticks):
                    jb = 0
                    for e in inputs.get(k, ()): jb |= M.JOYB[e]
                    R.L.joy = jb
                    try: ok = R.L.run_to([0x3A11], 4_000_000)
                    except RuntimeError: ok = False
                    if not ok: el.append('crash'); break
                    el.append(snap_emu(R))
                sc.append((boots, data, inputs, L0, el))
    res = []
    for alias, leave, ice in cands:
        model = dict(leave=leave, alias=alias, crash_arrive=set())
        score = 0
        for boots, data, inputs, L0, el in sc:
            OddGame.MODEL = {code: model}
            G = OddGame(list(data), tick=L0['tick'], R=L0['R'], row_above=L0['row_above']); G.sub = L0['sub']
            G.T[code] = [0, 0, flags_of(code, ice)]
            G.skates = 0x20 in boots; G.suction = 0x21 in boots; G.fire = 0x22 in boots
            if G.suction:
                for c in DE.FORCE_LEAVE: G.T[c][1] = 0
            dl = []
            for k in range(ticks):
                try: G.tick_once(set(inputs.get(k, ())))
                except (Crash, KeyError, RecursionError): dl.append('crash'); break
                dl.append(snap_doc(G))
            n = 0
            for a, b in zip(el, dl):
                if a != b: break
                n += 1
            score += n + (1 if len(el) == len(dl) == n else 0)
        res.append((score, alias, leave, ice))
    res.sort(key=lambda r: -r[0])
    return sum(len(s[-1]) + 1 for s in sc), res[:4]
