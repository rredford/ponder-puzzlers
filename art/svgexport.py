#!/usr/bin/env python3
"""Exports every sprite of the remake's artwork as an SVG file -> assets/svg/<name>.svg (+ sheet.svg, index.html).

The artwork in generate.py is drawn with a handful of PIL ImageDraw calls. This script runs the very same
drawing code against a recording back end that writes SVG elements instead of pixels, so the SVGs are the
original vector drawings (exact shapes, not traced bitmaps). Coordinates use the 192-unit drawing space of
generate.py; each file is displayed at 48x48 by default and scales freely."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate as G

C = G.C
OUT_DIR = os.path.join(G.ROOT, 'assets', 'svg')

def col(c):
    if c is None: return 'none', 1.0
    if isinstance(c, str): return c, 1.0
    r, g, b = c[:3]; a = c[3] if len(c) > 3 else 255
    return '#%02x%02x%02x' % (r, g, b), a / 255

def paint(fill=None, outline=None, width=0):
    f, fa = col(fill)
    s = [f'fill="{f}"']
    if f != 'none' and fa < 1: s.append(f'fill-opacity="{fa:.3f}"')
    if outline is not None and width:
        o, oa = col(outline)
        s.append(f'stroke="{o}" stroke-width="{width:g}"')
        if oa < 1: s.append(f'stroke-opacity="{oa:.3f}"')
    return ' '.join(s)

def n(v): return f'{v:.2f}'.rstrip('0').rstrip('.')

class SvgImage:
    def __init__(self, elems=None): self.elems = elems if elems is not None else []
    # PIL Image API used by generate.py
    def rotate(self, angle, resample=None):          # PIL: positive = counter-clockwise
        return SvgImage([f'<g transform="rotate({n(-angle)} {C / 2} {C / 2})">' + ''.join(self.elems) + '</g>'])
    def transpose(self, how):                          # only FLIP_LEFT_RIGHT is used
        return SvgImage([f'<g transform="translate({C} 0) scale(-1 1)">' + ''.join(self.elems) + '</g>'])
    def resize(self, size, resample=None): return self
    def body(self):
        # PIL paints translucent shapes by replacing pixels, so overlapping shapes of one translucent colour form
        # a flat union; reproduce that by drawing such runs opaque inside a group carrying the opacity.
        out, run, key = [], [], None
        import re
        def flush():
            if not run: return
            if len(run) == 1: out.append(run[0][0])
            else: out.append(f'<g opacity="{key[1]}">' + ''.join(e for _, e in run) + '</g>')
        for e in self.elems:
            m = re.search(r'(?:fill|stroke)="(#[0-9a-f]{6})"[^>]*?(?:fill|stroke)-opacity="([0-9.]+)"', e)
            k = (m.group(1), m.group(2)) if m and e.count('opacity=') == 1 else None
            if k and k == key: run.append((e, re.sub(r' (?:fill|stroke)-opacity="[0-9.]+"', '', e))); continue
            flush(); run, key = [], None
            if k: run, key = [(e, re.sub(r' (?:fill|stroke)-opacity="[0-9.]+"', '', e))], k
            else: out.append(e)
        flush()
        return ''.join(out)
    def svg(self, px=48):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{px}" height="{px}" viewBox="0 0 {C} {C}">'
                + self.body() + '</svg>\n')

def arc_point(box, ang):
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    a = math.radians(ang)
    return cx + rx * math.cos(a), cy + ry * math.sin(a), rx, ry

class SvgDraw:
    def __init__(self, img): self.img = img
    def _add(self, s): self.img.elems.append(s)
    @staticmethod
    def _box(xy):
        if len(xy) == 2 and not isinstance(xy[0], (int, float)): (x0, y0), (x1, y1) = xy
        else: x0, y0, x1, y1 = xy
        return x0, y0, x1, y1
    def rectangle(self, xy, fill=None, outline=None, width=1):
        x0, y0, x1, y1 = self._box(xy)
        w = width if outline is not None else 0
        i = w / 2                                      # PIL draws outlines inside the box
        self._add(f'<rect x="{n(x0 + i)}" y="{n(y0 + i)}" width="{n(x1 - x0 - 2 * i)}" height="{n(y1 - y0 - 2 * i)}" {paint(fill, outline, w)}/>')
    def rounded_rectangle(self, xy, radius=0, fill=None, outline=None, width=1):
        x0, y0, x1, y1 = self._box(xy)
        w = width if outline is not None else 0
        i = w / 2
        r = max(0, radius - i)
        self._add(f'<rect x="{n(x0 + i)}" y="{n(y0 + i)}" width="{n(x1 - x0 - 2 * i)}" height="{n(y1 - y0 - 2 * i)}" rx="{n(r)}" {paint(fill, outline, w)}/>')
    def ellipse(self, xy, fill=None, outline=None, width=1):
        x0, y0, x1, y1 = self._box(xy)
        w = width if outline is not None else 0
        i = w / 2
        self._add(f'<ellipse cx="{n((x0 + x1) / 2)}" cy="{n((y0 + y1) / 2)}" rx="{n(max(0, (x1 - x0) / 2 - i))}" ry="{n(max(0, (y1 - y0) / 2 - i))}" {paint(fill, outline, w)}/>')
    def polygon(self, pts, fill=None, outline=None, width=1):
        p = ' '.join(f'{n(x)},{n(y)}' for x, y in pts)
        self._add(f'<polygon points="{p}" {paint(fill, outline, width if outline is not None else 0)}/>')
    def line(self, pts, fill=None, width=1, joint=None):
        p = ' '.join(f'{n(x)},{n(y)}' for x, y in pts)
        c, a = col(fill)
        op = f' stroke-opacity="{a:.3f}"' if a < 1 else ''
        join = 'round' if joint == 'curve' else 'miter'
        self._add(f'<polyline points="{p}" fill="none" stroke="{c}" stroke-width="{width:g}" stroke-linejoin="{join}"{op}/>')
    def _arcpath(self, box, start, end, mode, inset=0):
        x0, y0, x1, y1 = box
        box = (x0 + inset, y0 + inset, x1 - inset, y1 - inset)
        sx, sy, rx, ry = arc_point(box, start)
        ex, ey, _, _ = arc_point(box, end)
        sweep = (end - start) % 360 or 360
        large = 1 if sweep > 180 else 0
        if sweep >= 360:                               # full circle: split in two
            mx, my, _, _ = arc_point(box, start + 180)
            d = f'M{n(sx)},{n(sy)} A{n(rx)},{n(ry)} 0 1 1 {n(mx)},{n(my)} A{n(rx)},{n(ry)} 0 1 1 {n(sx)},{n(sy)}'
        else:
            d = f'M{n(sx)},{n(sy)} A{n(rx)},{n(ry)} 0 {large} 1 {n(ex)},{n(ey)}'
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        if mode == 'chord': d += ' Z'
        elif mode == 'pie': d += f' L{n(cx)},{n(cy)} Z'
        return d
    def arc(self, xy, start, end, fill=None, width=1):
        c, a = col(fill)
        op = f' stroke-opacity="{a:.3f}"' if a < 1 else ''
        self._add(f'<path d="{self._arcpath(self._box(xy), start, end, "arc", width / 2)}" fill="none" stroke="{c}" stroke-width="{width:g}"{op}/>')
    def chord(self, xy, start, end, fill=None, outline=None, width=1):
        w = width if outline is not None else 0
        self._add(f'<path d="{self._arcpath(self._box(xy), start, end, "chord", w / 2)}" {paint(fill, outline, w)}/>')
    def pieslice(self, xy, start, end, fill=None, outline=None, width=1):
        w = width if outline is not None else 0
        self._add(f'<path d="{self._arcpath(self._box(xy), start, end, "pie", w / 2)}" {paint(fill, outline, w)}/>')
    def text(self, xy, s, font=None, fill=None, anchor=None):
        # Draw the glyphs as outlines (so the SVG does not depend on the font being installed).
        try:
            from fontTools.ttLib import TTFont
            from fontTools.pens.svgPathPen import SVGPathPen
            from fontTools.pens.boundsPen import BoundsPen
            tt = TTFont(getattr(font, 'path', G.FONT))
            gs = tt.getGlyphSet(); cmap = tt.getBestCmap(); upm = tt['head'].unitsPerEm
            size = getattr(font, 'size', 40); sc = size / upm
            names = [cmap[ord(ch)] for ch in s]
            adv = sum(gs[nm].width for nm in names)
            bp = BoundsPen(gs); x = 0
            for nm in names:
                from fontTools.pens.transformPen import TransformPen
                gs[nm].draw(TransformPen(bp, (1, 0, 0, 1, x, 0))); x += gs[nm].width
            xmin, ymin, xmax, ymax = bp.bounds
            # PIL anchor 'mm': horizontal middle of the advance, vertical middle between ascender and descender
            hh = tt['hhea']; mid_y = (hh.ascent + hh.descent) / 2
            ox = xy[0] - adv * sc / 2 if anchor == 'mm' else xy[0]
            oy = xy[1] + mid_y * sc if anchor == 'mm' else xy[1] + hh.ascent * sc
            c, a = col(fill); x = 0; parts = []
            for nm in names:
                pen = SVGPathPen(gs); gs[nm].draw(pen)
                parts.append(f'<path transform="translate({n(ox + x * sc)} {n(oy)}) scale({sc:.5f} {-sc:.5f})" d="{pen.getCommands()}" fill="{c}"/>')
                x += gs[nm].width
            self._add(''.join(parts)); return
        except Exception:
            pass
        c, a = col(fill)
        size = getattr(font, 'size', 40)
        anchor_attr = ' text-anchor="middle" dominant-baseline="central"' if anchor == 'mm' else ''
        self._add(f'<text x="{n(xy[0])}" y="{n(xy[1])}" font-family="Poppins, \'Arial Rounded MT Bold\', Arial, sans-serif" '
                  f'font-weight="700" font-size="{size}" fill="{c}"{anchor_attr}>{s}</text>')

class _ImageDrawModule:
    @staticmethod
    def Draw(img): return SvgDraw(img)

class _ImageModule:
    LANCZOS = BICUBIC = NEAREST = None
    FLIP_LEFT_RIGHT = 'flip'
    @staticmethod
    def new(mode, size, color=None): return SvgImage()

def main():
    G.ImageDraw = _ImageDrawModule
    G.Image = _ImageModule
    sprites = G.build()
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, img in sprites:
        with open(os.path.join(OUT_DIR, name + '.svg'), 'w') as f: f.write(img.svg())
    # one sheet with every sprite, and an HTML index with names
    cols = 16; rows = (len(sprites) + cols - 1) // cols
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{cols * 48}" height="{rows * 48}" viewBox="0 0 {cols * C} {rows * C}">']
    for i, (name, img) in enumerate(sprites):
        x, y = (i % cols) * C, (i // cols) * C
        parts.append(f'<svg id="{name}" x="{x}" y="{y}" width="{C}" height="{C}" viewBox="0 0 {C} {C}" overflow="hidden">' + img.body() + '</svg>')
    parts.append('</svg>\n')
    with open(os.path.join(OUT_DIR, 'sheet.svg'), 'w') as f: f.write(''.join(parts))
    cells = ''.join(f'<figure><img src="{nm}.svg" width="96" height="96" alt="{nm}"><figcaption>{nm}</figcaption></figure>' for nm, _ in sprites)
    with open(os.path.join(OUT_DIR, 'index.html'), 'w') as f:
        f.write('<!doctype html><meta charset="utf-8"><title>Ponder Puzzlers tiles (SVG)</title>'
                '<style>body{background:#22243a;color:#ccd;font:12px sans-serif;display:flex;flex-wrap:wrap;gap:8px;padding:12px}'
                'figure{margin:0;text-align:center}img{background:#2c2f4a;border-radius:4px}</style>' + cells)
    print(f'{len(sprites)} SVG sprites -> {OUT_DIR}')

if __name__ == '__main__':
    main()
