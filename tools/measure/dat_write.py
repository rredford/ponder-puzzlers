"""Write cartridge-format test levels (as used by the measure scripts) to a standard Chip's Challenge DAT file
with the Lynx ruleset signature, so they can be played in the remake or Tile World.
usage: dat_write.py OUT.dat TITLE PASSWORD LEVEL.bin [TIME]"""
import sys, struct
LYNX_TO_MS = {0x00: 0x00, 0x01: 0x01, 0x02: 0x0C, 0x0A: 0x1A, 0x0B: 0x1B, 0x0C: 0x1C, 0x0D: 0x1D, 0x25: 0x15, 0x0E: 0x29}
MONSTER_MS = {2: 0x40, 4: 0x44, 6: 0x48, 8: 0x4C, 5: 0x50, 11: 0x54, 9: 0x58, 10: 0x5C, 3: 0x60}   # + N/W/S/E
DIR_MS = {0: 0, 3: 1, 2: 2, 1: 3}
CHIP_MS = {0: 0x6C, 3: 0x6D, 2: 0x6E, 1: 0x6F}           # Chip facing N, W, S, E
def layer(cells):
    out = bytearray(); i = 0
    while i < len(cells):
        j = i
        while j < len(cells) and cells[j] == cells[i] and j - i < 255: j += 1
        n = j - i
        if n >= 4: out += bytes([0xFF, n, cells[i]])
        else: out += bytes(cells[i:j])
        i = j
    return bytes(out)
def level_record(num, data, title, password, time=0, hint=None):
    m = data[:1024]; st, xs, ys = data[1024:1152], data[1152:1280], data[1280:1408]
    top = [LYNX_TO_MS[b] for b in m]
    chips = sum(1 for b in m if b == 0x23)
    monsters = []
    for i in range(128):
        if not st[i]: continue
        c = (ys[i] // 8) * 32 + xs[i] // 8
        if i == 0: top[c] = CHIP_MS[st[i] & 3]; continue
        t = (st[i] >> 2) & 31
        top[c] = MONSTER_MS[t] + DIR_MS[st[i] & 3]
        monsters.append((xs[i] // 8, ys[i] // 8))
    l1 = layer(top); l2 = layer([0] * 1024)
    fields = bytes([3, len(title) + 1]) + title.encode() + b'\0'
    pw = bytes(c ^ 0x99 for c in password.encode()) + b'\0'
    fields += bytes([6, len(pw)]) + pw
    if hint: fields += bytes([7, len(hint) + 1]) + hint.encode() + b'\0'
    if monsters: fields += bytes([10, 2 * len(monsters)]) + bytes(b for m in monsters for b in m)
    body = struct.pack('<HHHH', num, time, chips, 1) + struct.pack('<H', len(l1)) + l1 + struct.pack('<H', len(l2)) + l2
    body += struct.pack('<H', len(fields)) + fields
    return struct.pack('<H', len(body)) + body
if __name__ == '__main__':
    out, title, pw, path = sys.argv[1:5]; time = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    data = open(path, 'rb').read()
    dat = struct.pack('<IH', 0x0102AAAC, 1) + level_record(1, data, title, pw, time)
    open(out, 'wb').write(dat)
    print('wrote', out, len(dat), 'bytes')
