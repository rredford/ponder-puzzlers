"""Replay a solution on the original (emulated) and stop at the first tick where any object crosses the map edge
(wraparound); used to tell edge-caused failures apart from others. run(rec, data) -> (outcome, tick, info)."""
import sys; sys.path.insert(0,'/tmp/claude-0'); sys.path.insert(0,'/home/claude/verify')
import emu_only as E, tws
from inject_run import inject
from clynx import CLynx
from lockstep import JOY
def wrapped(a, b):
    """8-bit coordinate went across the map edge (0..7 <-> 248..255)."""
    return (a < 8 and b >= 240) or (a >= 240 and b < 8)
def run(rec, data, extra=400):
    L = CLynx('/home/claude/rom/st_i.pkl'); inject(L, data)
    L.ram[0x0A] = 0; L.ram[0x3E] = 1; L.ram[0x39] = 10; L.joy = 0
    if not (L.run_to([0x39DF]) and L.run_to([0x3A11])): return 'crash', 0, None
    moves = {}
    for t, d in rec['moves']: moves[t] = moves.get(t, set()) | E.dirs(d)
    prev = [(L.ram[0x1000 + i], L.ram[0x1080 + i], L.ram[0x1100 + i]) for i in range(128)]
    for t in range(rec['moves'][-1][0] + extra):
        jb = 0
        for d in moves.get(t, ()): jb |= JOY[E.DM[d]]
        L.joy = jb
        try:
            if not L.run_to([0x3A11]): return 'crash', t, None
        except RuntimeError: return 'crash', t, None
        cur = [(L.ram[0x1000 + i], L.ram[0x1080 + i], L.ram[0x1100 + i]) for i in range(128)]
        for i in range(128):
            if cur[i][0] and prev[i][0] and (wrapped(prev[i][1], cur[i][1]) or wrapped(prev[i][2], cur[i][2])):
                side = 'W/E' if wrapped(prev[i][1], cur[i][1]) else 'N/S'
                return 'edge', t, (i, side, prev[i][1] // 8, prev[i][2] // 8)
        prev = cur
        if L.ram[0x28]: return 'win', t, None
        if L.ram[0x24]: return 'death', t, None
    return 'stall', None, None
