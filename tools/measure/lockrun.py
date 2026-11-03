"""Cartridge runs with one RAM byte locked (all writes to it ignored), for the sound-driver byte 795B."""
import sys, ctypes
sys.path.insert(0,'/tmp/claude-0'); sys.path.insert(0,'/home/claude/verify')
import clynxt5; from clynxt5 import CLynx, lib
lib.set_lock.argtypes=[ctypes.c_int]
import inject_run; inject_run.lib=lib
from inject_run import inject
import measure as M
class Run:
    def __init__(s, data, boots=None, lock=None):
        lib.set_lock(-1)
        s.L=CLynx('/home/claude/rom/st_i.pkl'); inject(s.L,data)
        s.L.ram[0x0A]=0; s.L.ram[0x3E]=1; s.L.ram[0x39]=10; s.L.joy=0
        s.ok=s.L.run_to([0x39DF],4_000_000) and s.L.run_to([0x3A11],4_000_000)
        for k,v in (boots or {}).items(): s.L.ram[k]=v
        if lock:
            a,v=lock; s.L.ram[a]=v; lib.set_lock(a)
        s.r=s.L.ram
    def tick(s, jb):
        s.L.joy=jb
        try: return s.L.run_to([0x3A11],4_000_000)
        except RuntimeError: return False
