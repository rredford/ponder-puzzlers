#!/usr/bin/env python3
"""Original level set "Pip's First Steps" -> assets/pip_levels.dat (standard DAT, MS tile codes)
plus assets/pip_levels_moves.txt (verified solutions, used by `levelpack check`)
and src/app/builtin_levels.hpp (the DAT embedded in the game binary)."""
import os, struct
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# legend -> MS/DAT tile code
TILE = {
    '#': 0x01, ' ': 0x00, 'c': 0x02, 'w': 0x03, 'f': 0x04, 'i': 0x0C, '%': 0x0B,
    '>': 0x13, '<': 0x14, '^': 0x12, 'v': 0x0D, 'E': 0x15, 'S': 0x22, 'T': 0x2B, 't': 0x27,
    '1': 0x17, '2': 0x16, '3': 0x19, '4': 0x18,              # doors: red blue yellow green
    'r': 0x65, 'b': 0x64, 'y': 0x67, 'g': 0x66,              # keys
    'K': 0x6A, 'u': 0x6B, 'F': 0x69, 'W': 0x68,              # skates suction fireboots flippers
    'q': 0x23, '=': 0x25, '-': 0x26, 'p': 0x28, 'x': 0x24, 'C': 0x31,
    'O': 0x29, '!': 0x2A, ':': 0x2D, 'P': 0x2E, '$': 0x1E, '&': 0x1F, '*': 0x2C, 'h': 0x2F, 'H': 0x21,
}
# objects: char -> top-layer code (bottom layer = floor)
OBJ = {'@': 0x6E, 'o': 0x0A}
MONSTER_BASE = {'bug': 0x40, 'fireball': 0x44, 'ball': 0x48, 'tank': 0x4C, 'glider': 0x50,
                'teeth': 0x54, 'walker': 0x58, 'blob': 0x5C, 'paramecium': 0x60}
DIRS = {'N': 0, 'W': 1, 'S': 2, 'E': 3}

LEVELS = [
 dict(title="First Steps", pw="STEP", time=120,
      hint="Collect every chip to open the socket, then step into the exit.",
      map=["#########",
           "#c  #  c#",
           "#   #   #",
           "#   @h  #",
           "## ### ##",
           "#c  S  c#",
           "####E####"],
      moves="LLDDLRUULUUDDRRRRRRUUDDLDDRLLLD"),
 dict(title="Lock and Key", pw="LOCK", time=150,
      hint="Keys open doors of the same colour. Green keys can be used again and again.",
      map=["###########",
           "#@  r1   c#",
           "#   ##   b#",
           "#2#########",
           "#  g   c  #",
           "#4######4##",
           "#c  S   c #",
           "####E######"],
      moves="RRRRRRRRDULLLLLLLLDDDRRRRRRRDDUULLLLLLLDDRRRD"),
 dict(title="Ice Rink", pw="RINK", time=120,
      hint="Ice keeps you sliding. Ice skates let you walk on it.",
      map=["###########",
           "#@ iiiiic #",
           "# ####### #",
           "#K iiiii  #",
           "# iciiici #",
           "# iiiiiii #",
           "####S######",
           "####E######"],
      moves="RRRDDLLLRDRRRRRDLLLDD"),
 dict(title="Conveyor Belts", pw="BELT", time=120,
      hint="Force floors push you along. Suction boots let you walk on them freely.",
      map=["###########",
           "#@ >>>>>c #",
           "######### #",
           "#u <<<<<< #",
           "#c#######v#",
           "######ES  #",
           "###########"],
      moves="RRRDDLLDURRRRRRRRDDLLL"),
 dict(title="Fire and Water", pw="HEAT", time=120,
      hint="Flippers let you swim. Fire boots let you walk through fire.",
      map=["###########",
           "#@  wc  F #",
           "#W####f####",
           "#  ffcff  #",
           "#####S#####",
           "#####E#####"],
      moves="DURRRRRRRLLDDLDD"),
 dict(title="Heavy Lifting", pw="HAUL", time=150,
      hint="Push blocks into water to fill it with dirt you can walk on.",
      map=["###########",
           "#@ o  w   #",
           "#########o#",
           "#E        #",
           "#         #",
           "###########"],
      moves="RRRRRRRRDDLLLLLLLL"),
 dict(title="Switchboard", pw="FLIP", time=120,
      hint="Green buttons swap the green walls between open and closed.",
      map=["###########",
           "#@ q =  c #",
           "######## ##",
           "#E S - q  #",
           "###########"],
      moves="RRRRRRRDDLLLLLLL"),
 dict(title="Portal Hop", pw="WARP", time=120,
      hint="Teleports send you to the previous teleport in reading order.",
      map=["###########",
           "#@ O#  c  #",
           "#S###     #",
           "#E###  O  #",
           "###########"],
      moves="RRUULRDDLLDD"),
 dict(title="Bug Patrol", pw="BUGS", time=200,
      hint="Bugs hug the wall on their left and chips block them. Follow behind it!",
      map=["###########",
           "#         #",
           "# c#####c #",
           "# ####### #",
           "#@####### #",
           "# ####### #",
           "# c#####c #",
           "#         #",
           "#####S#####",
           "#####E#####"],
      monsters=[('bug', 'E', 5, 1)],
      moves="UURLURRRRRRRRDLRDDDDLRDLLLLLLLUDRRRDD"),
 dict(title="Graduation", pw="GRAD", time=150,
      hint="Everything you have learned, all at once. Good luck, Pip!",
      map=["#############",
           "#@ r1 >>>> c#",
           "########### #",
           "#c  ffF wo  #",
           "#S###########",
           "#E###########"],
      moves="RRRRRRDDLLLLLLLLLLDD"),
]

def build_level(L, number, ox=10, oy=10):
    top = [0x01] * 1024; bottom = [0] * 1024
    for y in range(oy - 1, oy + len(L['map']) + 1):
        for x in range(ox - 1, ox + max(len(r) for r in L['map']) + 1):
            if 0 <= x < 32 and 0 <= y < 32: top[y * 32 + x] = 0x01
    chips = 0; monsters = []
    for r, row in enumerate(L['map']):
        for c, ch in enumerate(row):
            cell = (oy + r) * 32 + ox + c
            if ch in OBJ: top[cell] = OBJ[ch]
            else:
                top[cell] = TILE[ch]
                if ch == 'c': chips += 1
    for name, d, c, r in L.get('monsters', []):
        cell = (oy + r) * 32 + ox + c
        bottom[cell] = top[cell]; top[cell] = MONSTER_BASE[name] + DIRS[d]
        monsters.append((ox + c, oy + r))
    def rle(cells):
        out = bytearray(); i = 0
        while i < len(cells):
            j = i
            while j < len(cells) and cells[j] == cells[i] and j - i < 255: j += 1
            n = j - i
            if n >= 4: out += bytes([0xFF, n, cells[i]])
            else: out += bytes(cells[i:j])
            i = j
        return out
    opt = bytearray()
    def field(t, data): opt.extend([t, len(data)]); opt.extend(data)
    field(3, L['title'].encode() + b'\0')
    if L.get('hint'): field(7, L['hint'].encode() + b'\0')
    field(6, bytes(ord(ch) ^ 0x99 for ch in L['pw']) + b'\0')
    if monsters: field(10, bytes(v for xy in monsters for v in xy))
    lt, lb = rle(top), rle(bottom)
    rec = struct.pack('<HHHH', number, L['time'], chips, 1)
    rec += struct.pack('<H', len(lt)) + lt + struct.pack('<H', len(lb)) + lb + struct.pack('<H', len(opt)) + opt
    return struct.pack('<H', len(rec)) + rec

def main():
    data = bytearray(struct.pack('<IH', 0x0102AAAC, len(LEVELS)))
    for n, L in enumerate(LEVELS, 1): data += build_level(L, n)
    os.makedirs(os.path.join(ROOT, 'assets'), exist_ok=True)
    open(os.path.join(ROOT, 'assets', 'pip_levels.dat'), 'wb').write(data)
    with open(os.path.join(ROOT, 'assets', 'pip_levels_moves.txt'), 'w') as f:
        f.write("# Verified solutions for Pip's First Steps (levelpack check assets/pip_levels.dat this-file)\n")
        for n, L in enumerate(LEVELS, 1):
            if L.get('moves'): f.write('%d: %s\n' % (n, L['moves']))
    with open(os.path.join(ROOT, 'src', 'app', 'builtin_levels.hpp'), 'w') as f:
        f.write('// GENERATED by art/levels.py - original level set "Pip\'s First Steps".\n#pragma once\n#include <cstdint>\n#include <cstddef>\n')
        f.write('inline const uint8_t kBuiltinLevels[] = {\n')
        for i in range(0, len(data), 20): f.write('  ' + ','.join(str(b) for b in data[i:i + 20]) + ',\n')
        f.write('};\ninline constexpr size_t kBuiltinLevelsSize = sizeof(kBuiltinLevels);\n')
    print('levels:', len(LEVELS), 'bytes:', len(data))

if __name__ == '__main__':
    main()
