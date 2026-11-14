#!/usr/bin/env python3
"""Generates the remake's ORIGINAL artwork (no ROM data is used).

Everything is drawn procedurally with PIL at 4x resolution and downsampled to
48x48 cells. Output:
  assets/atlas.rgba      raw RGBA atlas: 8-byte header (u32 width, u32 height) + pixels
  assets/atlas_preview.png
  src/app/atlas_index.hpp  generated sprite index (name -> cell)
  assets/font_*.rgba     baked UI fonts (Poppins Bold, SIL OFL) + glyph tables
"""
import math, os, struct, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = 48
SS = 4                    # supersampling
C = CELL * SS              # canvas size per cell
OUT = (27, 24, 43, 255)   # outline colour

def rgba(h, a=255):
    h = h.lstrip('#'); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

def canvas():
    return Image.new('RGBA', (C, C), (0, 0, 0, 0))

def P(v): return v * SS   # design units are 48-px space
def PW(v): return max(1, int(round(v * SS)))

def rr(d, box, r, fill, outline=OUT, w=2):
    d.rounded_rectangle([P(box[0]), P(box[1]), P(box[2]), P(box[3])], radius=P(r), fill=fill,
                        outline=outline, width=PW(w) if outline else 0)

def ell(d, box, fill, outline=OUT, w=2):
    d.ellipse([P(box[0]), P(box[1]), P(box[2]), P(box[3])], fill=fill, outline=outline, width=PW(w) if outline else 0)

def poly(d, pts, fill, outline=OUT, w=2):
    pts = [(P(x), P(y)) for x, y in pts]
    d.polygon(pts, fill=fill)
    if outline: d.line(pts + [pts[0]], fill=outline, width=PW(w), joint='curve')

def line(d, pts, fill, w=2):
    d.line([(P(x), P(y)) for x, y in pts], fill=fill, width=PW(w), joint='curve')

def finish(img):
    return img.resize((CELL, CELL), Image.LANCZOS)

# ------------------------------------------------------------------ tiles
FLOOR = rgba('#c9d3e3'); FLOOR_D = rgba('#a9b6cc'); FLOOR_L = rgba('#e4eaf4')

def floor(img=None):
    img = img or canvas(); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=FLOOR)
    d.rectangle([P(1), P(1), P(47), P(47)], outline=FLOOR_D, width=PW(2))
    d.line([(P(2), P(2)), (P(46), P(2))], fill=FLOOR_L, width=PW(2))
    d.line([(P(2), P(2)), (P(2), P(46))], fill=FLOOR_L, width=PW(2))
    for (x, y) in ((6, 6), (42, 6), (6, 42), (42, 42)):
        ell(d, (x - 1.3, y - 1.3, x + 1.3, y + 1.3), FLOOR_D, None)
    return img

def raised(base, light, dark, img=None):
    img = img or canvas(); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=dark)
    rr(d, (2, 2, 46, 46), 6, base, OUT, 1.5)
    d.polygon([(P(5), P(5)), (P(43), P(5)), (P(38), P(10)), (P(10), P(10)), (P(10), P(38)), (P(5), P(43))], fill=light)
    rr(d, (10, 10, 38, 38), 3, base, None)
    return img

def wall(): return raised(rgba('#5b6b8c'), rgba('#8496ba'), rgba('#3a4560'))
def bluewall():
    img = raised(rgba('#2f7de1'), rgba('#7fb7ff'), rgba('#1c4f9a')); d = ImageDraw.Draw(img)
    line(d, [(15, 33), (33, 15)], rgba('#ffffff', 120), 2); line(d, [(20, 35), (35, 20)], rgba('#ffffff', 70), 1.5)
    return img

def ice(img=None):
    img = img or canvas(); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=rgba('#bdeefc'))
    d.rectangle([P(1), P(1), P(47), P(47)], outline=rgba('#8fd3ea'), width=PW(2))
    for a, b in (((8, 18), (18, 8)), ((14, 36), (36, 14)), ((30, 40), (40, 30))):
        line(d, [a, b], rgba('#ffffff', 230), 2.5)
    ell(d, (34, 8, 38, 12), rgba('#ffffff'), None)
    return img

def dirt():
    img = canvas(); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=rgba('#8a5a33'))
    rnd = random.Random(3)
    for _ in range(26):
        x, y, r = rnd.uniform(4, 44), rnd.uniform(4, 44), rnd.uniform(1, 2.6)
        ell(d, (x - r, y - r, x + r, y + r), rgba(rnd.choice(['#6b4224', '#a8774b', '#5a361b'])), None)
    d.rectangle([P(1), P(1), P(47), P(47)], outline=rgba('#5a361b'), width=PW(2))
    return img

def gravel():
    img = canvas(); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=rgba('#9aa0a8'))
    rnd = random.Random(9)
    for _ in range(34):
        x, y, r = rnd.uniform(4, 44), rnd.uniform(4, 44), rnd.uniform(1.4, 3.0)
        ell(d, (x - r, y - r * 0.8, x + r, y + r * 0.8), rgba(rnd.choice(['#c7ccd3', '#7d838c', '#b3b8bf'])), rgba('#5d636b'), 0.7)
    return img

def arrow_pts(cx, cy, s):  # chevron pointing north
    return [(cx - s, cy + s * 0.5), (cx, cy - s * 0.5), (cx + s, cy + s * 0.5), (cx + s * 0.55, cy + s * 0.9), (cx, cy + s * 0.15), (cx - s * 0.55, cy + s * 0.9)]

def force(direction, phase, colors=None):
    img = canvas(); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=rgba('#2c3e3a'))
    d.rectangle([P(1), P(1), P(47), P(47)], outline=rgba('#1c2826'), width=PW(2))
    cols = colors or [rgba('#3fe08a'), rgba('#a6f55a'), rgba('#3fe08a'), rgba('#1fa864')]
    for k in range(-1, 3):
        cy = 40 - k * 16 - phase * 4
        if cy < -6 or cy > 54: continue
        poly(d, arrow_pts(24, cy, 9), cols[(k + phase) % len(cols)], rgba('#10201c'), 1)
    img = img.rotate(-90 * direction, resample=Image.BICUBIC)
    return img

def force_random(phase):
    cols = [rgba('#ff6b6b'), rgba('#ffd93d'), rgba('#6bcBff'), rgba('#c77dff')]
    return force(phase % 4, 0, [cols[phase % 4], cols[(phase + 1) % 4]])

def ice_corner(walls):
    img = ice(); d = ImageDraw.Draw(img)
    wc, wl = rgba('#5b6b8c'), rgba('#8496ba')
    # walls: set of 'N','E','S','W'
    if 'N' in walls: rr(d, (-4, -4, 52, 8), 3, wc, OUT, 1.5); line(d, [(2, 3), (46, 3)], wl, 1.5)
    if 'S' in walls: rr(d, (-4, 40, 52, 52), 3, wc, OUT, 1.5)
    if 'W' in walls: rr(d, (-4, -4, 8, 52), 3, wc, OUT, 1.5); line(d, [(3, 2), (3, 46)], wl, 1.5)
    if 'E' in walls: rr(d, (40, -4, 52, 52), 3, wc, OUT, 1.5)
    # curved inner fillet
    corner = {frozenset('NW'): (8, 8, 0), frozenset('NE'): (40, 8, 1), frozenset('SE'): (40, 40, 2), frozenset('SW'): (8, 40, 3)}[frozenset(walls)]
    x, y, q = corner
    r = 12
    box = (x - r, y - r, x + r, y + r)
    start = {0: 0, 1: 90, 2: 180, 3: 270}[q]
    d.pieslice([P(v) for v in box], start, start + 90, fill=wc)
    return img

def teleport(phase):
    img = floor(); d = ImageDraw.Draw(img)
    ell(d, (5, 5, 43, 43), rgba('#2a1a4a'), OUT, 2)
    for k in range(5):
        a0 = phase * 40 + k * 72
        r = 16 - k * 2.6
        d.arc([P(24 - r), P(24 - r), P(24 + r), P(24 + r)], a0, a0 + 200,
              fill=rgba(['#b388ff', '#7c4dff', '#e1bee7', '#9575cd', '#ffffff'][k]), width=PW(2.4))
    ell(d, (21, 21, 27, 27), rgba('#ffffff'), None)
    return img

def fire(phase):
    img = canvas(); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=rgba('#5a1d0e'))
    rnd = random.Random(phase * 7 + 1)
    for layer, col in ((0, '#ff5722'), (1, '#ff9800'), (2, '#ffeb3b')):
        for k in range(3):
            cx = 10 + k * 14 + rnd.uniform(-2, 2)
            h = (30 - layer * 8) + rnd.uniform(-4, 4)
            w = 9 - layer * 2
            poly(d, [(cx - w, 46), (cx - w * 0.6, 46 - h * 0.5), (cx + rnd.uniform(-3, 3), 46 - h), (cx + w * 0.6, 46 - h * 0.5), (cx + w, 46)],
                 rgba(col), rgba('#7a2108') if layer == 0 else None, 1)
    return img

def water(phase):
    img = canvas(); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=rgba('#1e64c8'))
    for row in range(4):
        y = 8 + row * 11
        off = (phase * 4 + row * 6) % 16
        pts = [(x, y + 2.2 * math.sin((x + off) / 16 * 2 * math.pi)) for x in range(-2, 52, 2)]
        line(d, pts, rgba('#7fc4ff') if row % 2 == 0 else rgba('#4a95e8'), 2)
    return img

def boot_base(color, sole):
    img = floor(); d = ImageDraw.Draw(img)
    poly(d, [(15, 8), (27, 8), (27, 28), (38, 30), (40, 37), (13, 37)], rgba(color))
    rr(d, (12, 36, 41, 41), 2, rgba(sole))
    line(d, [(17, 12), (25, 12)], rgba('#ffffff', 140), 1.5)
    return img, d

def skates():
    img, d = boot_base('#eceff1', '#90a4ae')
    line(d, [(12, 44), (42, 44)], rgba('#cfd8dc'), 2.5); line(d, [(16, 41), (16, 44)], OUT, 1.5); line(d, [(36, 41), (36, 44)], OUT, 1.5)
    return img
def fireboots():
    img, d = boot_base('#e53935', '#6d1b14')
    poly(d, [(20, 30), (23, 18), (26, 26), (28, 20), (31, 30)], rgba('#ffca28'), None)
    return img
def suction():
    img, d = boot_base('#43a047', '#1b5e20')
    for x in (16, 26, 36): ell(d, (x - 3, 39, x + 3, 45), rgba('#cddc39'), OUT, 1)
    return img
def flippers():
    img = floor(); d = ImageDraw.Draw(img)
    poly(d, [(18, 10), (30, 10), (38, 40), (24, 44), (10, 40)], rgba('#29b6f6'))
    for x in (17, 24, 31): line(d, [(x, 20), (x - 1 if x < 24 else x + 1 if x > 24 else x, 40)], rgba('#0277bd'), 1.5)
    rr(d, (17, 8, 31, 15), 3, rgba('#0277bd'))
    return img

def thief():
    img = floor(); d = ImageDraw.Draw(img)
    poly(d, [(8, 44), (12, 18), (24, 6), (36, 18), (40, 44)], rgba('#37474f'))
    ell(d, (14, 16, 34, 34), rgba('#ffcc80'))
    rr(d, (13, 20, 35, 26), 2, rgba('#212121'), None)
    ell(d, (17, 21, 22, 25), rgba('#ffffff'), None); ell(d, (26, 21, 31, 25), rgba('#ffffff'), None)
    ell(d, (19, 22, 21, 24), OUT, None); ell(d, (28, 22, 30, 24), OUT, None)
    line(d, [(19, 30), (29, 30)], rgba('#6d4c41'), 1.5)
    return img

def popup():
    img = floor(); d = ImageDraw.Draw(img)
    for x in range(10, 40, 6):
        for y in (10, 38): ell(d, (x - 1.5, y - 1.5, x + 1.5, y + 1.5), rgba('#6b7a99'), None)
    for y in range(16, 38, 6):
        for x in (10, 38): ell(d, (x - 1.5, y - 1.5, x + 1.5, y + 1.5), rgba('#6b7a99'), None)
    return img

def toggle(closed, phase):
    img = floor()
    d = ImageDraw.Draw(img)
    if closed:
        rr(d, (3, 3, 45, 45), 5, rgba('#2e9e5b', 230), None)
        d.polygon([(P(6), P(6)), (P(42), P(6)), (P(38), P(10)), (P(10), P(10)), (P(10), P(38)), (P(6), P(42))], fill=rgba('#6fe39b', 200))
    # marching dashes around the border
    per = [(4, 4), (44, 4), (44, 44), (4, 44)]
    total = 160
    for k in range(10):
        t0 = (k * 16 + phase * 4) % total
        for t in (t0, t0 + 7):
            pass
        a = t0; b = (t0 + 8)
        def pt(t):
            t %= total; side = int(t // 40); f = (t % 40) / 40
            x0, y0 = per[side]; x1, y1 = per[(side + 1) % 4]
            return (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
        line(d, [pt(a), pt(a + 4), pt(b)], rgba('#14532d') if closed else rgba('#22a35a'), 2.4)
    return img

def button(color, ring):
    img = floor(); d = ImageDraw.Draw(img)
    rr(d, (9, 9, 39, 39), 6, rgba('#7d879c'))
    ell(d, (14, 13, 34, 33), rgba(ring), None)
    ell(d, (14, 11, 34, 31), rgba(color))
    ell(d, (18, 14, 25, 19), rgba('#ffffff', 150), None)
    return img

def door(color, dark):
    img = canvas(); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=rgba(dark))
    rr(d, (4, 3, 44, 47), 4, rgba(color))
    for x in (13, 24, 35): line(d, [(x, 7), (x, 43)], rgba(dark), 1.5)
    ell(d, (20, 20, 28, 28), rgba('#263238'))
    poly(d, [(22.5, 26), (25.5, 26), (27, 34), (21, 34)], rgba('#263238'), None)
    return img

def key(color, dark):
    img = floor(); d = ImageDraw.Draw(img)
    ell(d, (8, 8, 24, 24), rgba(color)); ell(d, (13, 13, 19, 19), FLOOR, OUT, 1.5)
    poly(d, [(21, 19), (40, 34), (37, 38), (33, 35), (31, 38), (28, 35), (18, 22)], rgba(color))
    line(d, [(11, 12), (15, 10)], rgba('#ffffff', 170), 1.5)
    return img

def chipitem():
    img = floor(); d = ImageDraw.Draw(img)
    for k in range(4):
        for side in (0, 1):
            x = 14 + k * 6.5
            if side == 0: rr(d, (x - 1.5, 7, x + 1.5, 14), 0.5, rgba('#f6c445'), OUT, 0.8)
            else: rr(d, (x - 1.5, 34, x + 1.5, 41), 0.5, rgba('#f6c445'), OUT, 0.8)
    for k in range(4):
        y = 14 + k * 6.5
        rr(d, (7, y - 1.5, 14, y + 1.5), 0.5, rgba('#f6c445'), OUT, 0.8)
        rr(d, (34, y - 1.5, 41, y + 1.5), 0.5, rgba('#f6c445'), OUT, 0.8)
    rr(d, (12, 12, 36, 36), 3, rgba('#263238'))
    ell(d, (15, 15, 19, 19), rgba('#607d8b'), None)
    line(d, [(19, 29), (29, 29)], rgba('#f6c445'), 1.2); line(d, [(19, 25), (26, 25)], rgba('#f6c445'), 1.2)
    return img

def socket():
    img = raised(rgba('#78909c'), rgba('#b0bec5'), rgba('#455a64')); d = ImageDraw.Draw(img)
    rr(d, (15, 15, 33, 33), 2, rgba('#263238'))
    for k in range(4):
        x = 18 + k * 4
        line(d, [(x, 16), (x, 13)], rgba('#f6c445'), 1.4); line(d, [(x, 32), (x, 35)], rgba('#f6c445'), 1.4)
    return img

def exitportal(phase):
    img = floor(); d = ImageDraw.Draw(img)
    glow = ['#4dd0e1', '#80deea', '#b2ebf2'][phase]
    rr(d, (5, 5, 43, 43), 6, rgba('#006064'))
    rr(d, (9, 9, 39, 39), 4, rgba(glow), None)
    rr(d, (14 - phase, 14 - phase, 34 + phase, 34 + phase), 3, rgba('#e0f7fa'), None)
    poly(d, [(24, 15), (32, 24), (27, 24), (27, 33), (21, 33), (21, 24), (16, 24)], rgba('#00838f'), None)
    return img

def thin(edges):
    img = floor(); d = ImageDraw.Draw(img)
    if 'E' in edges: rr(d, (41, -2, 50, 50), 2, rgba('#5b6b8c'), OUT, 1.5)
    if 'S' in edges: rr(d, (-2, 41, 50, 50), 2, rgba('#5b6b8c'), OUT, 1.5)
    if 'N' in edges: rr(d, (-2, -2, 50, 7), 2, rgba('#5b6b8c'), OUT, 1.5)
    if 'W' in edges: rr(d, (-2, -2, 7, 50), 2, rgba('#5b6b8c'), OUT, 1.5)
    return img

def bomb():
    img = floor(); d = ImageDraw.Draw(img)
    ell(d, (9, 13, 39, 43), rgba('#263238'))
    rr(d, (20, 9, 28, 15), 1.5, rgba('#546e7a'))
    line(d, [(24, 9), (28, 5), (33, 6)], rgba('#8d6e63'), 1.6)
    poly(d, [(34, 2), (36, 5), (39, 5), (37, 7), (38, 10), (35, 8), (32, 10), (33, 7), (31, 5), (34, 5)], rgba('#ffd54f'), None)
    ell(d, (15, 18, 21, 24), rgba('#ffffff', 120), None)
    return img

def trap():
    img = floor(); d = ImageDraw.Draw(img)
    rr(d, (5, 5, 43, 43), 4, rgba('#6d4c41'))
    rr(d, (9, 9, 39, 39), 3, rgba('#3e2723'), None)
    for k in range(6):
        x = 11 + k * 5
        poly(d, [(x, 16), (x + 2.5, 22), (x + 5, 16)], rgba('#cfd8dc'), rgba('#78909c'), 0.6)
        poly(d, [(x, 32), (x + 2.5, 26), (x + 5, 32)], rgba('#cfd8dc'), rgba('#78909c'), 0.6)
    return img

def cloner():
    img = raised(rgba('#37474f'), rgba('#607d8b'), rgba('#263238')); d = ImageDraw.Draw(img)
    for k, (dx, dy) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):
        cx, cy = 24 + dx * 9, 24 + dy * 9
        poly(d, [(cx + dx * 4, cy + dy * 4), (cx - dy * 3.5 - dx * 2, cy + dx * 3.5 - dy * 2), (cx + dy * 3.5 - dx * 2, cy - dx * 3.5 - dy * 2)], rgba('#ffb300'), None)
    ell(d, (20, 20, 28, 28), rgba('#ffb300'), OUT, 1.2)
    return img

def hint():
    img = floor(); d = ImageDraw.Draw(img)
    ell(d, (8, 6, 40, 36), rgba('#ffffff'))
    poly(d, [(16, 32), (14, 42), (24, 34)], rgba('#ffffff'), None)
    font = ImageFont.truetype(FONT, P(24))
    d.text((P(24), P(21)), '?', font=font, fill=rgba('#3949ab'), anchor='mm')
    return img

# ------------------------------------------------------------------ creatures (drawn facing north)
def rotate(img, d): return img.rotate(-90 * d, resample=Image.BICUBIC)

def bug(frame):
    img = canvas(); d = ImageDraw.Draw(img)
    sw = [0, 2, 0, -2][frame]
    for k, y in enumerate((18, 25, 32)):
        o = sw if k % 2 == 0 else -sw
        line(d, [(17, y), (8, y - 3 + o)], OUT, 2); line(d, [(31, y), (40, y - 3 - o)], OUT, 2)
    ell(d, (14, 14, 34, 40), rgba('#e53935'))
    line(d, [(24, 15), (24, 39)], OUT, 1.5)
    for (x, y) in ((19, 26), (29, 30), (20, 34)): ell(d, (x - 2, y - 2, x + 2, y + 2), OUT, None)
    ell(d, (17, 6, 31, 18), rgba('#263238'))
    ell(d, (19, 9, 23, 13), rgba('#ffffff'), None); ell(d, (25, 9, 29, 13), rgba('#ffffff'), None)
    line(d, [(20, 7), (16, 2)], OUT, 1.5); line(d, [(28, 7), (32, 2)], OUT, 1.5)
    return img

def paramecium(frame):
    img = canvas(); d = ImageDraw.Draw(img)
    for k in range(5):
        y = 10 + k * 7
        x = 24 + 3 * math.sin((k + frame) * 1.4)
        line(d, [(x - 9, y), (x - 13, y + 2)], OUT, 1.5); line(d, [(x + 9, y), (x + 13, y + 2)], OUT, 1.5)
        ell(d, (x - 9, y - 5, x + 9, y + 5), rgba('#7cb342' if k % 2 else '#9ccc65'), OUT, 1.5)
    ell(d, (19, 6, 22, 9), OUT, None); ell(d, (26, 6, 29, 9), OUT, None)
    return img

def fireball(frame):
    img = canvas(); d = ImageDraw.Draw(img)
    rnd = random.Random(frame + 11)
    for k in range(8):
        a = k / 8 * 2 * math.pi + frame * 0.4
        r = 14 + rnd.uniform(0, 5)
        poly(d, [(24 + math.cos(a - 0.35) * 10, 24 + math.sin(a - 0.35) * 10), (24 + math.cos(a) * r, 24 + math.sin(a) * r),
                 (24 + math.cos(a + 0.35) * 10, 24 + math.sin(a + 0.35) * 10)], rgba('#ff7043'), None)
    ell(d, (12, 12, 36, 36), rgba('#ff9800'))
    ell(d, (16, 16, 32, 32), rgba('#ffd54f'), None)
    ell(d, (20, 19, 25, 24), rgba('#fffde7'), None)
    return img

def glider(frame):
    img = canvas(); d = ImageDraw.Draw(img)
    f = [0, 1.5, 0, -1.5][frame]
    poly(d, [(24, 5), (42, 38 + f), (24, 31), (6, 38 - f)], rgba('#b3e5fc'))
    poly(d, [(24, 5), (24, 31), (6, 38 - f)], rgba('#81d4fa'), OUT, 1.5)
    ell(d, (19, 16, 29, 26), rgba('#0288d1'))
    ell(d, (21, 18, 25, 22), rgba('#ffffff'), None)
    return img

def ball(frame):
    img = canvas(); d = ImageDraw.Draw(img)
    sq = [0, 1.5, 3, 1.5][frame]
    ell(d, (10 - sq, 10 + sq, 38 + sq, 38 - sq), rgba('#ec407a'))
    ell(d, (15, 14, 23, 20), rgba('#ffffff', 190), None)
    d.arc([P(13), P(13), P(35), P(35)], 200, 300, fill=rgba('#ad1457'), width=PW(1.5))
    return img

def block():
    img = canvas(); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, C, C], fill=rgba('#7b4a24'))
    rr(d, (2, 2, 46, 46), 3, rgba('#c98a4b'))
    rr(d, (7, 7, 41, 41), 2, rgba('#b37538'), rgba('#7b4a24'), 1.5)
    line(d, [(8, 8), (40, 40)], rgba('#7b4a24'), 3); line(d, [(40, 8), (8, 40)], rgba('#7b4a24'), 3)
    line(d, [(4, 4), (44, 4)], rgba('#e8b27a'), 1.5)
    return img

def tank(frame):
    img = canvas(); d = ImageDraw.Draw(img)
    t = frame % 2
    for x in (8, 34):
        rr(d, (x, 8, x + 6, 42), 2, rgba('#37474f'))
        for k in range(5): line(d, [(x, 11 + k * 7 + t * 3), (x + 6, 11 + k * 7 + t * 3)], rgba('#90a4ae'), 1)
    rr(d, (13, 12, 35, 40), 4, rgba('#1e88e5'))
    ell(d, (17, 19, 31, 33), rgba('#1565c0'))
    rr(d, (22, 3, 26, 24), 1, rgba('#0d47a1'))
    return img

def walker(frame):
    img = canvas(); d = ImageDraw.Draw(img)
    s = [0, 3, 0, -3][frame]
    for (sx, sy, o) in ((-1, -1, s), (1, -1, -s), (-1, 1, -s), (1, 1, s)):
        line(d, [(24 + sx * 8, 24 + sy * 6), (24 + sx * 17, 24 + sy * 15 + o)], OUT, 3)
        ell(d, (24 + sx * 17 - 2.5, 24 + sy * 15 + o - 2.5, 24 + sx * 17 + 2.5, 24 + sy * 15 + o + 2.5), rgba('#ce93d8'), OUT, 1)
    ell(d, (12, 12, 36, 36), rgba('#ab47bc'))
    ell(d, (17, 16, 22, 21), rgba('#ffffff'), None); ell(d, (26, 16, 31, 21), rgba('#ffffff'), None)
    ell(d, (18.5, 17, 21, 19.5), OUT, None); ell(d, (27.5, 17, 30, 19.5), OUT, None)
    return img

def blob(frame):
    img = canvas(); d = ImageDraw.Draw(img)
    pts = []
    for k in range(16):
        a = k / 16 * 2 * math.pi
        r = 15 + 2.5 * math.sin(a * 3 + frame * 1.6)
        pts.append((24 + math.cos(a) * r, 25 + math.sin(a) * r))
    poly(d, pts, rgba('#66bb6a'))
    ell(d, (15, 14, 22, 20), rgba('#c8e6c9', 200), None)
    ell(d, (19, 22, 23, 26), OUT, None); ell(d, (26, 22, 30, 26), OUT, None)
    return img

def teeth(frame):
    img = canvas(); d = ImageDraw.Draw(img)
    o = [2, 6, 9, 6][frame]
    ell(d, (6, 6, 42, 44), rgba('#7e57c2'))
    for k in range(10):
        a = k / 10 * 2 * math.pi
        line(d, [(24 + math.cos(a) * 17, 25 + math.sin(a) * 18), (24 + math.cos(a) * 21, 25 + math.sin(a) * 22)], rgba('#5e35b1'), 2)
    rr(d, (11, 22 - o / 2, 37, 30 + o / 2), 4, rgba('#4a148c'))
    for k in range(5):
        x = 13 + k * 5
        poly(d, [(x, 22 - o / 2), (x + 2.5, 26 - o / 2 + 1), (x + 5, 22 - o / 2)], rgba('#ffffff'), None)
        poly(d, [(x, 30 + o / 2), (x + 2.5, 26 + o / 2 - 1), (x + 5, 30 + o / 2)], rgba('#ffffff'), None)
    ell(d, (15, 10, 21, 16), rgba('#ffeb3b')); ell(d, (27, 10, 33, 16), rgba('#ffeb3b'))
    ell(d, (17, 12, 19, 14), OUT, None); ell(d, (29, 12, 31, 14), OUT, None)
    return img

# ---- the hero (original design: "Pip" — teal cap, orange hoodie, purple trousers, backpack)
SKIN = rgba('#ffcc99'); HOOD = rgba('#ff8f00'); HOOD_D = rgba('#e65100'); CAP = rgba('#00897b'); PANTS = rgba('#5e35b1'); SHOE = rgba('#37474f'); BAG = rgba('#43a047')

def hero(direction, frame, pose='walk'):
    img = canvas(); d = ImageDraw.Draw(img)
    step = [0, 2.5, 0, -2.5][frame] if pose == 'walk' else 0
    arm = 3 if pose == 'push' else 0
    if direction in (N, S):
        back = direction == N
        # legs
        rr(d, (17, 31 + max(0, step), 23, 43 + step * 0.4), 2, PANTS); rr(d, (25, 31 + max(0, -step), 31, 43 - step * 0.4), 2, PANTS)
        ell(d, (15.5, 40 + step * 0.4, 23.5, 45 + step * 0.4), SHOE); ell(d, (24.5, 40 - step * 0.4, 32.5, 45 - step * 0.4), SHOE)
        # body
        if back: rr(d, (15, 17, 33, 30), 4, BAG)
        rr(d, (14, 17, 34, 34), 6, HOOD)
        if back: rr(d, (16, 18, 32, 31), 4, BAG); line(d, [(18, 22), (30, 22)], rgba('#2e7d32'), 1.5)
        else: line(d, [(24, 22), (24, 33)], HOOD_D, 1.4); ell(d, (21, 26, 27, 30), HOOD_D, None)
        # arms
        ay = -arm * 2 if direction == N else arm
        # sleeves and hands sized to match the pushing pose (hero_push)
        rr(d, (6.5, 19 + ay, 15.5, 31 + ay), 4, HOOD); rr(d, (32.5, 19 + ay, 41.5, 31 + ay), 4, HOOD)
        ell(d, (6.5, 27.5 + ay, 15.5, 36.5 + ay), SKIN); ell(d, (32.5, 27.5 + ay, 41.5, 36.5 + ay), SKIN)
        # head
        ell(d, (14, 3, 34, 22), SKIN)
        if back:
            ell(d, (14, 3, 34, 22), rgba('#6d4c41'))                      # back of the head: hair
            line(d, [(18, 17), (20, 20)], rgba('#4e342e'), 1.2); line(d, [(28, 17), (26, 20)], rgba('#4e342e'), 1.2)
            d.chord([P(13), P(2), P(35), P(20)], 180, 360, fill=CAP, outline=OUT, width=PW(2))
            ell(d, (21, 1, 27, 6), rgba('#26a69a'), OUT, 1.2)            # cap button
        else:
            d.chord([P(13), P(1), P(35), P(19)], 180, 360, fill=CAP, outline=OUT, width=PW(2))
            rr(d, (16, 8.5, 32, 11), 1, rgba('#00695c'), None)
            ell(d, (18, 12, 22, 16), OUT, None); ell(d, (26, 12, 30, 16), OUT, None)
            ell(d, (19, 12.5, 20.5, 14), rgba('#ffffff'), None); ell(d, (27, 12.5, 28.5, 14), rgba('#ffffff'), None)
            d.arc([P(20), P(14), P(28), P(20)], 20, 160, fill=OUT, width=PW(1.4))
            ell(d, (15.5, 15, 18.5, 17.5), rgba('#ff8a80', 160), None); ell(d, (29.5, 15, 32.5, 17.5), rgba('#ff8a80', 160), None)
    else:
        # side view facing east; west is mirrored
        rr(d, (19 + step, 31, 25 + step, 43), 2, PANTS); rr(d, (23 - step, 31, 29 - step, 43), 2, PANTS)
        ell(d, (18 + step, 40, 28 + step, 45), SHOE); ell(d, (22 - step, 40, 32 - step, 45), SHOE)
        rr(d, (11, 18, 21, 31), 3, BAG)
        rr(d, (16, 17, 32, 34), 6, HOOD)
        ax = arm * 2
        rr(d, (20 - step + ax, 20, 28 - step + ax, 31), 4, HOOD_D); ell(d, (20.5 - step + ax, 27, 27.5 - step + ax, 36), SKIN)
        ell(d, (15, 3, 35, 22), SKIN)
        d.chord([P(14), P(1), P(36), P(19)], 180, 360, fill=CAP, outline=OUT, width=PW(2))
        rr(d, (28, 8.5, 40, 11), 1.5, rgba('#00695c'))
        ell(d, (27, 12, 31, 16), OUT, None); ell(d, (28, 12.5, 29.5, 14), rgba('#ffffff'), None)
        d.arc([P(26), P(15), P(33), P(20)], 20, 120, fill=OUT, width=PW(1.4))
        ell(d, (17, 12, 22, 16), rgba('#6d4c41'), None)
        if direction == W: img = img.transpose(Image.FLIP_LEFT_RIGHT)
    return img

def limb(d, p0, p1, fill, w):
    """A rounded, outlined sleeve/leg from p0 to p1 (design units)."""
    for col, ww in ((OUT, w + 2), (fill, w)):
        line(d, [p0, p1], col, ww)
        for (x, y) in (p0, p1): ell(d, (x - ww / 2, y - ww / 2, x + ww / 2, y + ww / 2), col, None)

def hand_flat(d, cx, cy, wide, tall):
    """An open palm seen flat-on, with finger creases."""
    ell(d, (cx - wide / 2, cy - tall / 2, cx + wide / 2, cy + tall / 2), SKIN)
    for k in (-1, 1):
        line(d, [(cx + k * wide * 0.18, cy - tall * 0.42), (cx + k * wide * 0.18, cy - tall * 0.05)], rgba('#d9a066'), 0.9)

def hero_push(direction):
    """Pushing/straining: arms raised to near horizontal, palms out in front, body leaning in."""
    img = canvas(); d = ImageDraw.Draw(img)
    if direction in (N, S):
        back = direction == N
        # braced stance: feet apart
        rr(d, (15, 31, 22, 43), 2, PANTS); rr(d, (26, 31, 33, 43), 2, PANTS)
        ell(d, (13, 40, 22, 45), SHOE); ell(d, (26, 40, 35, 45), SHOE)
        if back:
            # arms reach away from us: shoulders and upper arms visible, hands peek out beside the head
            limb(d, (14, 21), (12, 13), HOOD, 6); limb(d, (34, 21), (36, 13), HOOD, 6)
            rr(d, (15, 17, 33, 30), 4, BAG); rr(d, (14, 17, 34, 34), 6, HOOD)
            rr(d, (16, 18, 32, 31), 4, BAG); line(d, [(18, 22), (30, 22)], rgba('#2e7d32'), 1.5)
            ell(d, (14, 3, 34, 22), rgba('#6d4c41'))
            line(d, [(18, 17), (20, 20)], rgba('#4e342e'), 1.2); line(d, [(28, 17), (26, 20)], rgba('#4e342e'), 1.2)
            d.chord([P(13), P(2), P(35), P(20)], 180, 360, fill=CAP, outline=OUT, width=PW(2))
            ell(d, (21, 1, 27, 6), rgba('#26a69a'), OUT, 1.2)
            ell(d, (7, 6.5, 16, 15.5), SKIN); ell(d, (32, 6.5, 41, 15.5), SKIN)
        else:
            rr(d, (14, 18, 34, 34), 6, HOOD)
            line(d, [(24, 23), (24, 33)], HOOD_D, 1.4)
            # arms come straight at us: short foreshortened sleeves, big palms facing out at chest height
            limb(d, (13, 22), (17, 27), HOOD, 7); limb(d, (35, 22), (31, 27), HOOD, 7)
            hand_flat(d, 16.5, 28, 9, 10); hand_flat(d, 31.5, 28, 9, 10)
            ell(d, (14, 4, 34, 23), SKIN)
            d.chord([P(13), P(2), P(35), P(20)], 180, 360, fill=CAP, outline=OUT, width=PW(2))
            rr(d, (16, 9.5, 32, 12), 1, rgba('#00695c'), None)
            # squeezed-shut eyes and gritted teeth: straining
            line(d, [(18, 15), (20.5, 14), (22, 15)], OUT, 1.4); line(d, [(26, 15), (27.5, 14), (30, 15)], OUT, 1.4)
            rr(d, (20, 17.5, 28, 20.5), 1, rgba('#ffffff'), OUT, 1.2); line(d, [(24, 17.8), (24, 20.2)], OUT, 0.8)
            ell(d, (15.5, 16, 18.5, 18.5), rgba('#ff8a80', 170), None); ell(d, (29.5, 16, 32.5, 18.5), rgba('#ff8a80', 170), None)
        return img
    # side view facing east, leaning into the push; west is mirrored
    lean = 3
    limb(d, (22, 33), (14, 42), PANTS, 6)                      # back leg braced far behind
    ell(d, (8, 39.5, 18, 45), SHOE)
    limb(d, (26, 33), (28, 42), PANTS, 6)                      # front leg under the body
    ell(d, (24, 39.5, 34, 45), SHOE)
    limb(d, (27 + lean, 23), (38, 25), HOOD_D, 5)              # far arm, behind the body
    hand_flat(d, 40.5, 24, 5, 8)
    rr(d, (10 + lean, 18, 20 + lean, 31), 3, BAG)
    poly(d, [(15, 34), (31, 34), (34 + lean, 18), (18 + lean, 17)], HOOD)   # torso tilted forward
    limb(d, (25 + lean, 24), (38, 27), HOOD, 6)                # near arm: horizontal, reaching forward
    hand_flat(d, 41, 27, 5.5, 9)                             # palm flat against what's being pushed
    ox = lean + 1
    ell(d, (15 + ox, 3, 35 + ox, 22), SKIN)
    d.chord([P(14 + ox), P(1), P(36 + ox), P(19)], 180, 360, fill=CAP, outline=OUT, width=PW(2))
    rr(d, (28 + ox, 8.5, 40 + ox, 11), 1.5, rgba('#00695c'))
    line(d, [(27 + ox, 14), (29.5 + ox, 13.5), (31 + ox, 14.5)], OUT, 1.4)        # squinting eye
    line(d, [(28.5 + ox, 18.5), (30.5 + ox, 17.8), (32.5 + ox, 18.5)], OUT, 1.4)  # grimace
    ell(d, (17 + ox, 12, 22 + ox, 16), rgba('#6d4c41'), None)
    ell(d, (20 + ox, 4.5, 23 + ox, 8.5), rgba('#81d4fa'), OUT, 0.9)               # bead of sweat
    if direction == W: img = img.transpose(Image.FLIP_LEFT_RIGHT)
    return img

# ------------------------------------------------------------------ effects
def explosion(k):
    img = canvas(); d = ImageDraw.Draw(img)
    r = 6 + k * 4; a = max(0, 255 - k * 40)
    rnd = random.Random(k)
    for j in range(10):
        ang = j / 10 * 2 * math.pi
        rr_ = r + rnd.uniform(0, 6)
        poly(d, [(24 + math.cos(ang - 0.3) * r * 0.5, 24 + math.sin(ang - 0.3) * r * 0.5), (24 + math.cos(ang) * rr_, 24 + math.sin(ang) * rr_),
                 (24 + math.cos(ang + 0.3) * r * 0.5, 24 + math.sin(ang + 0.3) * r * 0.5)], rgba('#ff7043', a), None)
    ell(d, (24 - r * 0.6, 24 - r * 0.6, 24 + r * 0.6, 24 + r * 0.6), rgba('#ffee58', a), None)
    return img

def smoke(k):
    img = canvas(); d = ImageDraw.Draw(img)
    a = max(0, 230 - k * 35)
    for j in range(6):
        ang = j / 6 * 2 * math.pi + k * 0.3
        r = 5 + k * 2.2
        cx, cy = 24 + math.cos(ang) * k * 2.5, 24 + math.sin(ang) * k * 2.5 - k
        ell(d, (cx - r, cy - r, cx + r, cy + r), rgba('#cfd8dc', a), None)
    return img

def splash(k):
    img = canvas(); d = ImageDraw.Draw(img)
    a = max(0, 255 - k * 38)
    for j in range(2):
        r = 5 + k * 3.2 - j * 5
        if r > 0: d.ellipse([P(24 - r), P(24 - r * 0.7), P(24 + r), P(24 + r * 0.7)], outline=rgba('#e3f2fd', a), width=PW(2))
    for j in range(6):
        ang = j / 6 * 2 * math.pi
        rr_ = 4 + k * 3
        x, y = 24 + math.cos(ang) * rr_, 24 + math.sin(ang) * rr_ * 0.7 - (6 - abs(k - 3) * 2)
        ell(d, (x - 1.8, y - 1.8, x + 1.8, y + 1.8), rgba('#90caf9', a), None)
    return img

# ------------------------------------------------------------------ assemble
N, E, S, W = 0, 1, 2, 3
def find_font():
    """Locate Poppins Bold: $PONDER_FONT, common install paths, then fontconfig."""
    import os, glob, subprocess
    env = os.environ.get('PONDER_FONT')
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [os.path.join(here, 'Poppins-Bold.ttf'),
             '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf']
    for pat in ('~/.local/share/fonts/**/Poppins-Bold.ttf', '~/.fonts/**/Poppins-Bold.ttf',
                '/usr/share/fonts/**/Poppins-Bold.ttf', '/usr/local/share/fonts/**/Poppins-Bold.ttf'):
        cands += glob.glob(os.path.expanduser(pat), recursive=True)
    for c in cands:
        if os.path.isfile(c):
            return c
    try:
        out = subprocess.run(['fc-match', '-f', '%{file}', 'Poppins:bold'],
                             capture_output=True, text=True).stdout.strip()
        if os.path.basename(out).lower() == 'poppins-bold.ttf':
            return out
    except OSError:
        pass
    raise SystemExit('Poppins-Bold.ttf not found. Install Poppins (SIL OFL, '
                     'https://fonts.google.com/specimen/Poppins), put Poppins-Bold.ttf in art/, '
                     'or set PONDER_FONT=/path/to/Poppins-Bold.ttf')

FONT = find_font()

def build():
    sprites = []   # (name, image)
    add = lambda n, im: sprites.append((n, finish(im)))
    tiles = {
        0x00: floor, 0x01: wall, 0x02: ice, 0x03: dirt, 0x04: bluewall,
        0x0F: skates, 0x10: fireboots, 0x11: suction, 0x12: flippers, 0x15: thief, 0x16: popup,
        0x19: lambda: button('#43a047', '#1b5e20'), 0x22: lambda: button('#1e88e5', '#0d47a1'),
        0x2E: lambda: button('#8d6e63', '#4e342e'), 0x30: lambda: button('#e53935', '#8e0000'),
        0x1A: lambda: door('#e53935', '#7f0000'), 0x1B: lambda: door('#1e88e5', '#0d3c75'),
        0x1C: lambda: door('#fdd835', '#8a7300'), 0x1D: lambda: door('#43a047', '#1b5e20'),
        0x1E: lambda: key('#e53935', '#7f0000'), 0x1F: lambda: key('#1e88e5', '#0d3c75'),
        0x20: lambda: key('#fdd835', '#8a7300'), 0x21: lambda: key('#43a047', '#1b5e20'),
        0x23: chipitem, 0x24: socket, 0x26: floor, 0x27: floor, 0x28: gravel,
        0x29: lambda: thin('E'), 0x2A: lambda: thin('S'), 0x2B: lambda: thin('ES'),
        0x34: lambda: thin('N'), 0x35: lambda: thin('W'),          # extended mode only
        0x2C: bomb, 0x2D: trap, 0x2F: cloner, 0x31: chipitem, 0x32: bluewall, 0x33: hint,
        0x0A: lambda: ice_corner('NW'), 0x0B: lambda: ice_corner('NE'), 0x0C: lambda: ice_corner('SE'), 0x0D: lambda: ice_corner('SW'),
    }
    for code, fn in sorted(tiles.items()): add('tile_%02X' % code, fn())
    for dd, name in enumerate('NESW'):
        for ph in range(4): add('force_%s_%d' % (name, ph), force(dd, ph))
    for ph in range(4): add('force_R_%d' % ph, force_random(ph))
    for ph in range(3):
        add('teleport_%d' % ph, teleport(ph)); add('fire_%d' % ph, fire(ph)); add('water_%d' % ph, water(ph)); add('exit_%d' % ph, exitportal(ph))
    for ph in range(4):
        add('toggleopen_%d' % ph, toggle(False, ph)); add('toggleclosed_%d' % ph, toggle(True, ph))
    creatures = {2: bug, 3: paramecium, 4: fireball, 5: glider, 6: ball, 8: tank, 9: walker, 10: blob, 11: teeth}
    for t, fn in sorted(creatures.items()):
        for f in range(4):
            base = fn(f)
            for dd in range(4):
                im = base if t in (4, 6, 10) else rotate(base, dd)   # round creatures don't rotate
                add('obj_%d_%d_%d' % (t, dd, f), im)
    add('obj_7', block())
    for dd in range(4):
        for f in range(4): add('hero_%d_%d' % (dd, f), hero(dd, f))
        add('heropush_%d' % dd, hero_push(dd))
    for k in range(6):
        add('fx_explode_%d' % k, explosion(k)); add('fx_smoke_%d' % k, smoke(k)); add('fx_splash_%d' % k, splash(k))
    return sprites

def write_atlas(sprites):
    cols = 16
    rows = (len(sprites) + cols - 1) // cols
    atlas = Image.new('RGBA', (cols * CELL, rows * CELL), (0, 0, 0, 0))
    index = []
    for i, (name, im) in enumerate(sprites):
        x, y = (i % cols) * CELL, (i // cols) * CELL
        atlas.paste(im, (x, y))
        index.append((name, x, y))
    os.makedirs(os.path.join(ROOT, 'assets'), exist_ok=True)
    with open(os.path.join(ROOT, 'assets', 'atlas.rgba'), 'wb') as f:
        f.write(struct.pack('<II', atlas.width, atlas.height)); f.write(atlas.tobytes())
    prev = Image.new('RGBA', atlas.size, (40, 42, 54, 255)); prev.alpha_composite(atlas)
    prev.resize((atlas.width * 2, atlas.height * 2), Image.NEAREST).save(os.path.join(ROOT, 'assets', 'atlas_preview.png'))
    with open(os.path.join(ROOT, 'src', 'app', 'atlas_index.hpp'), 'w') as f:
        f.write('// GENERATED by art/generate.py — do not edit.\n#pragma once\n#include <string_view>\n\n')
        f.write('struct AtlasEntry { std::string_view name; int x, y; };\nconstexpr int kAtlasCell = %d;\n' % CELL)
        f.write('constexpr AtlasEntry kAtlas[] = {\n')
        for name, x, y in index: f.write('  {"%s", %d, %d},\n' % (name, x, y))
        f.write('};\n')
    print('atlas', atlas.size, len(sprites), 'sprites')

def write_font(px, name):
    font = ImageFont.truetype(FONT, px)
    chars = [chr(c) for c in range(32, 127)]
    cw = max(font.getbbox(c)[2] for c in chars) + 4
    asc, desc = font.getmetrics(); ch = asc + desc + 4
    img = Image.new('RGBA', (cw * 16, ch * 6), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    widths = []
    for i, c in enumerate(chars):
        x, y = (i % 16) * cw + 2, (i // 16) * ch + 2
        d.text((x, y), c, font=font, fill=(255, 255, 255, 255))
        widths.append(int(font.getlength(c)))
    with open(os.path.join(ROOT, 'assets', 'font_%s.rgba' % name), 'wb') as f:
        f.write(struct.pack('<IIII', img.width, img.height, cw, ch)); f.write(bytes(widths)); f.write(img.tobytes())

if __name__ == '__main__':
    os.makedirs(os.path.join(ROOT, 'src', 'app'), exist_ok=True)
    write_atlas(build())
    write_font(16, 'small'); write_font(26, 'large')
