"""Outcome of each TWS solution on the ORIGINAL (emulated), levels injected; no spec-engine lock-step.
usage: emu_only.py LEVELDIR SOL.tws OUT.tsv [lo hi]"""
import sys, json
sys.path.insert(0, '/home/claude/verify')
from inject_run import inject
from clynx import CLynx
from lockstep import JOY
import tws
TWDIR = {0: {'N'}, 1: {'W'}, 2: {'S'}, 3: {'E'}}
import doc_engine as DE
DM = {'N': DE.N, 'E': DE.E, 'S': DE.S, 'W': DE.W}
def dirs(d):
    # TWS direction codes: 0-3 N W S E; 4-7 the diagonals NW, SW, NE, SE (as inject_run.TWDIR and the remake decode
    # them; an earlier version here combined codes 4-15 wrongly)
    return [{'N'}, {'W'}, {'S'}, {'E'}, {'N', 'W'}, {'S', 'W'}, {'N', 'E'}, {'S', 'E'}][d] if d < 8 else set()
def run(rec, data, extra=400):
    L = CLynx('/home/claude/rom/st_i.pkl'); inject(L, data)
    L.ram[0x0A] = 0; L.ram[0x3E] = 1; L.ram[0x39] = 10; L.joy = 0
    if not (L.run_to([0x39DF]) and L.run_to([0x3A11])): return 'crash', 0
    moves = {}
    for t, d in rec['moves']: moves[t] = moves.get(t, set()) | dirs(d)
    end = rec['moves'][-1][0] + extra
    for t in range(end):
        jb = 0
        for d in moves.get(t, ()): jb |= JOY[DM[d]]
        L.joy = jb
        try:
            if not L.run_to([0x3A11]): return 'crash', t
        except RuntimeError: return 'crash', t
        r = L.ram
        if r[0x28]: return 'win', t
        if r[0x24]: return ('time-out' if r[0x3D] == 1 else 'death'), t
    return 'stall', None
if __name__ == '__main__':
    ldir, twsf, outf = sys.argv[1:4]
    lo, hi = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (1, 99999)
    s = tws.parse(twsf); out = open(outf, 'w')
    for rec in s['recs']:
        if rec['moves'] is None or not (lo <= rec['level'] <= hi): continue
        try: data = open('%s/%d.bin' % (ldir, rec['level']), 'rb').read()
        except FileNotFoundError: continue
        if data == b'\xff': continue
        o, t = run(rec, data)
        out.write('%d\t%d\t%s\t%s\n' % (rec['level'], rec['total'], o, '' if t is None else t)); out.flush()
