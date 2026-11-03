#!/usr/bin/env python3
"""Newly composed music for Ponder Puzzlers -> assets/audio/music_XX.song.

15 original pieces fill the cartridge's music slots (spec doc 08 §5.4): 13 level tunes, the title and the
ending. Melodies are hand-written below; bass, chords, arpeggios, drums and harmony lines are arranged
from each tune's chord chart by the helpers in this file. Nothing is derived from the cartridge's music.

Notation: notes are `name+octave.length` in 16th notes (`c5.4` = C5 quarter note, `f#5.2`, `bb4.6`),
`r.N` is a rest, `|` separates bars (checked)."""
import os, re

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'audio')
SUB = 3                                    # synth ticks per 16th note (tpb = 12) - room for swing

PC = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}
def pitch_class(name):
    name = name.lower()
    pc = PC[name[0]]
    for ch in name[1:]:
        pc += 1 if ch == '#' else -1 if ch == 'b' else 0
    return pc % 12

def midi(tok):
    m = re.fullmatch(r'([a-g][#b]?)(-?\d)', tok)
    if not m: raise ValueError('bad note ' + tok)
    name, octv = m.groups()
    base = PC[name[0]] + (1 if '#' in name else -1 if (len(name) > 1 and name[1] == 'b') else 0)
    return 12 * (int(octv) + 1) + base

QUAL = {'': [0, 4, 7], 'm': [0, 3, 7], '7': [0, 4, 7, 10], 'm7': [0, 3, 7, 10], 'maj7': [0, 4, 7, 11],
        'sus4': [0, 5, 7], 'sus2': [0, 2, 7], 'dim': [0, 3, 6], '6': [0, 4, 7, 9], 'm6': [0, 3, 7, 9]}
def chord(sym):
    m = re.fullmatch(r'([A-G][#b]?)(.*)', sym)
    root, q = m.groups()
    return pitch_class(root.lower()), QUAL[q]

def melody(text, bar):
    """-> list of (start16, len16, midi or None) and check bar lengths"""
    out, t = [], 0
    for bi, b in enumerate(text.split('|')):
        b = b.strip()
        if not b: continue
        start = t
        for tok in b.split():
            name, ln = tok.rsplit('.', 1); ln = int(ln)
            out.append((t, ln, None if name == 'r' else midi(name)))
            t += ln
        if t - start != bar: raise ValueError(f'bar {bi + 1} has {t - start} sixteenths, expected {bar}: {b}')
    return out, t

SCALES = {'major': [0, 2, 4, 5, 7, 9, 11], 'minor': [0, 2, 3, 5, 7, 8, 10, 11]}   # minor incl. raised 7th

def harmony_below(note, key_pc, mode):
    for iv in (3, 4, 5):
        if (note - iv - key_pc) % 12 in SCALES[mode]: return note - iv
    return note - 3

# ---------------------------------------------------------------- instruments
BASE_INSTS = {
    'lead':  dict(wave='pulse', duty=0.25, pwm=0.06, pwmrate=0.4, a=0.008, d=0.25, s=0.55, r=0.12, vib=0.12, vibrate=5.5,
                  vibdelay=0.25, cutoff=5500, gain=0.21, pan=0.1, delay=0.22, verb=0.2, mono=1),
    'lead2': dict(wave='saw', mix2=0.5, detune=8, cutoff=2400, fenv=1500, fdecay=0.2, a=0.01, d=0.3, s=0.5, r=0.15,
                  gain=0.09, pan=-0.35, delay=0.2, verb=0.25, mono=1),
    'bell':  dict(wave='sine', mix2=0.3, oct2=2, detune=3, a=0.002, d=0.6, s=0.0, r=0.4, gain=0.10, pan=0.35, verb=0.35, delay=0.3),
    'bass':  dict(wave='saw', cutoff=650, fenv=900, fdecay=0.1, res=0.2, a=0.002, d=0.15, s=0.6, r=0.06, gain=0.24, sub=0.35, mono=1),
    'arp':   dict(wave='pulse', duty=0.125, a=0.001, d=0.09, s=0.1, r=0.05, gain=0.06, cutoff=4500, pan=-0.25, delay=0.3, verb=0.15),
    'pad':   dict(wave='saw', mix2=0.7, detune=12, cutoff=1100, a=0.4, d=0.5, s=0.8, r=0.6, gain=0.045, verb=0.5),
    'kick':  dict(wave='sine', pslide=20, pdecay=0.035, a=0.001, d=0.18, s=0.0, r=0.05, gain=0.5),
    'snare': dict(wave='noise', noiserate=30, a=0.001, d=0.12, s=0.0, r=0.06, cutoff=6000, hp=200, gain=0.18, verb=0.2),
    'snrtone': dict(wave='tri', pslide=5, pdecay=0.03, a=0.001, d=0.06, s=0.0, r=0.03, gain=0.12),
    'hat':   dict(wave='noise', noiserate=60, hp=7000, a=0.001, d=0.03, s=0.0, r=0.02, gain=0.07, pan=0.2),
    'ohat':  dict(wave='noise', noiserate=60, hp=6000, a=0.001, d=0.14, s=0.0, r=0.06, gain=0.05, pan=0.2),
    'tick':  dict(wave='metal', noiserate=8, hp=3000, a=0.001, d=0.02, s=0.0, r=0.01, gain=0.06, pan=-0.2),
    'shaker': dict(wave='noise', noiserate=50, hp=5000, a=0.01, d=0.05, s=0.0, r=0.03, gain=0.035, pan=0.3),
}

# accompaniment styles: bass pattern (tokens R 3 5 7 8 6, '-' rest, .len in 16ths), arpeggio (indices, step), drums (16ths)
STYLES = {
    'march':  dict(bass='R.2 R.2 8.2 R.2 5.2 R.2 8.2 5.2', arp=None,
                   drums={'kick': 'x.......x.x.....', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'}),
    'bounce': dict(bass='R.4 5.4 8.4 5.4', arp=('0 1 2 3 2 1', 2),
                   drums={'kick': 'x.......x.......', 'snare': '....x.......x...', 'hat': '..x...x...x...x.'}),
    'swing':  dict(bass='R.4 3.4 5.4 6.4', arp=None,
                   drums={'kick': 'x.......x.......', 'snare': '....x.......x...', 'hat': 'x...x.x.x...x.x.'}),
    'waltz':  dict(bass='R.4 5.4 5.4', arp=('0 1 2 3 2 1', 2),
                   drums={'kick': 'x...........', 'hat': '....o...o...'}),
    'drive':  dict(bass='R.2 R.2 8.2 R.2 R.2 R.2 8.2 R.2', arp=('0 2 1 3', 1),
                   drums={'kick': 'x.....x...x.....', 'snare': '....x.......x...', 'hat': 'xoxoxoxoxoxoxoxo'}),
    'latin':  dict(bass='R.6 5.6 8.4', arp=('0 1 2 1', 2),
                   drums={'kick': 'x.....x.x.......', 'snare': 'o..o..o...o.o...', 'shaker': 'xoxoxoxoxoxoxoxo'}),
    'quirky': dict(bass='R.2 -.2 5.2 -.2 8.2 -.2 5.2 -.2', arp=None,
                   drums={'kick': 'x...x...x...x...', 'snare': '....x..o....x..o', 'hat': '..x...x...x...x.'}),
    'mystery': dict(bass='R.8 5.8', arp=('0 2 1 2', 4),
                   drums={'kick': 'x.......x.......', 'hat': 'o...o...o...o...'}),
    'anthem': dict(bass='R.2 R.2 R.2 R.2 5.2 5.2 8.2 5.2', arp=('0 1 2 3', 2),
                   drums={'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'hat': '..x...x...x...x.', 'ohat': '..............x.'}),
    'clock':  dict(bass='R.4 5.4 R.4 5.4', arp=('0 2 1 2 3 2 1 2', 1),
                   drums={'kick': 'x.......x.......', 'snare': '....x.......x...', 'tick': 'x.x.x.x.x.x.x.x.'}),
    'gentle': dict(bass='R.8 5.8', arp=('0 1 2 3 2 1 0 1', 2),
                   drums={}),
}

def chord_tone(tok, root, tones):
    return {'R': 0, '3': tones[1], '5': tones[2], '8': 12, '7': tones[3] if len(tones) > 3 else 10, '6': 9}[tok] + root

def arrange(song):
    bar = song.get('bar', 16)
    key_pc, mode = pitch_class(song['key']), song['mode']
    style = STYLES[song['style']]
    insts = {k: dict(v) for k, v in BASE_INSTS.items()}
    for k, v in song.get('insts', {}).items(): insts.setdefault(k, {}); insts[k].update(v)
    notes = []                       # (tick16, inst, midi, len16, vel)
    def add(t, inst, m, ln, vel): notes.append((t, inst, m, ln, vel))

    sections = {}
    for name, sec in song['sections'].items():
        mel, total = melody(sec['mel'], bar)
        chords = sec['chords'].split()
        if total != bar * len(chords): raise ValueError(f"{song['file']} {name}: {total // bar} melody bars, {len(chords)} chords")
        sections[name] = (mel, chords)

    first_chords = sections['A'][1][:2]
    form = [('intro', None)] + [(n, n[0]) for n in song['form']]
    t = 0
    loop_tick = None
    prev_pad = None
    for idx, (part, sec) in enumerate(form):
        if part == 'intro':
            mel, chords, variant = [], first_chords, 'intro'
        else:
            mel, chords = sections[sec]
            variant = part
        if idx == 1: loop_tick = t
        for bi, sym in enumerate(chords):
            bt = t + bi * bar
            root, tones = chord(sym)
            broot = 36 + root if 36 + root <= 43 else 24 + root
            # bass
            bpos = 0
            for tok in style['bass'].split():
                kind, ln = tok.rsplit('.', 1); ln = int(ln)
                if kind != '-': add(bt + bpos, 'bass', broot + chord_tone(kind, 0, tones), max(1, ln - (1 if ln > 2 else 0)), 0.9 if bpos == 0 else 0.75)
                bpos += ln
            # pad: chord tones voiced into the 55..67 window
            pad = sorted(((root + iv - 55) % 12) + 55 for iv in tones[:4])
            for m in pad: add(bt, 'pad', m, bar, 0.8)
            prev_pad = pad
            # arpeggio (not in the first statement of A, to let the tune breathe)
            if style['arp'] and variant not in ('A',):
                pat, step = style['arp']
                idxs = [int(x) for x in pat.split()]
                ext = [root + iv for iv in tones[:3]] + [root + 12 + iv for iv in tones[:3]]
                ext = [60 + ((p - 60) % 12) + (12 if p - root >= 12 else 0) for p in ext]
                k = 0
                for pos in range(0, bar, step):
                    add(bt + pos, 'arp', ext[idxs[k % len(idxs)] % len(ext)], step, 0.8 if pos % 4 == 0 else 0.6)
                    k += 1
            # drums (intro: kick + hats only; fills at the end of each B)
            for inst, pat in style['drums'].items():
                if variant == 'intro' and inst in ('snare',): continue
                for pos, ch in enumerate(pat[:bar]):
                    if ch in 'xo':
                        v = 1.0 if ch == 'x' else 0.55
                        add(bt + pos, inst, 50 if inst == 'snrtone' else 60, 1, v)
                        if inst == 'snare': add(bt + pos, 'snrtone', 50, 1, v)
            if variant[0] == 'B' and bi == len(chords) - 1 and 'snare' in style['drums']:
                for pos in range(bar // 2, bar):
                    add(bt + pos, 'snare', 60, 1, 0.35 + 0.6 * (pos - bar // 2) / (bar // 2))
        # melody
        for (st, ln, m) in mel:
            if m is None: continue
            vel = 0.95 if st % 4 == 0 else 0.8
            add(t + st, 'lead', m, ln, vel)
            if variant.endswith('2'):          # second statement: harmony line + bell doubling
                add(t + st, 'lead2', harmony_below(m, key_pc, mode), ln, 0.8)
                if st % 4 == 0: add(t + st, 'bell', m + 12, min(ln, 4), 0.6)
        t += len(chords) * bar
    return insts, notes, t, loop_tick

MIX = {}
_mixf = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mix.json')
if os.path.exists(_mixf):
    import json
    MIX = json.load(open(_mixf))

def write_song(song):
    insts, notes, length, loop_tick = arrange(song)
    trims = MIX.get(song['file'], {})
    for k, v in insts.items():
        v['gain'] = round(v.get('gain', 0.5) * trims.get(k, 1.0) * trims.get('_master', 1.0), 4)
    swing = song.get('swing', 0)
    lines = [f"# {song['title']} - original composition for Ponder Puzzlers", f"name {song['title']}",
             f"tempo {song['tempo']}", f"tpb {4 * SUB}", f"echo {song.get('echo', 0.75)} {song.get('feedback', 0.3)}"]
    used = sorted({n[1] for n in notes})
    for k in used:
        lines.append(f"inst {k} " + " ".join(f"{a}={b}" for a, b in insts[k].items()))
    for (t16, inst, m, ln, vel) in sorted(notes):
        t = t16 * SUB + (swing if (t16 % 4 == 2 and swing) else 0)
        lines.append(f"n {t} {inst} {m} {ln * SUB} {vel:.2f}")
    lines.append(f"length {length * SUB}")
    lines.append(f"loop {loop_tick * SUB if song.get('loops', True) else -1}")
    path = os.path.join(OUT, f"music_{song['file']}.song")
    with open(path, 'w') as f: f.write("\n".join(lines) + "\n")
    return path, length / 4 * 60 / song['tempo']

# ---------------------------------------------------------------- the music
FORM = ['A', 'A2', 'B', 'A3']

SONGS = [
 dict(file='title', title='Circuit Hero', tempo=140, key='C', mode='major', style='march', form=FORM,
      insts={'lead': dict(duty=0.3)},
      sections={'A': dict(chords='C G Am F C G F G', mel=
        'e5.4 g5.4 c6.6 b5.2 | d6.4 b5.4 g5.8 | a5.4 c6.4 e6.6 d6.2 | c6.4 a5.4 f5.8 |'
        'e5.2 f5.2 g5.4 c6.4 e6.4 | d6.6 c6.2 b5.4 g5.4 | a5.4 c6.4 f6.4 e6.2 d6.2 | d6.12 r.4'),
                'B': dict(chords='Am Em F C Dm Am G G', mel=
        'c6.6 b5.2 a5.4 e5.4 | g5.6 a5.2 b5.8 | a5.4 c6.4 f6.4 e6.4 | e6.6 d6.2 c6.8 |'
        'd6.4 f6.4 a5.4 d6.4 | c6.6 b5.2 a5.8 | b5.4 d6.4 g6.4 f6.4 | d6.8 g5.4 b5.4')}),
 dict(file='ending', title='Homecoming', tempo=92, key='F', mode='major', style='gentle', form=FORM, echo=1.0, feedback=0.4,
      insts={'lead': dict(wave='tri', gain=0.26, vib=0.15, verb=0.35), 'arp': dict(wave='sine', mix2=0.25, oct2=1, gain=0.06, d=0.2)},
      sections={'A': dict(chords='F C Dm Bb F C Bb C', mel=
        'a5.6 g5.2 f5.4 c5.4 | e5.8 g5.8 | f5.6 e5.2 d5.4 a5.4 | bb5.12 a5.4 |'
        'a5.6 bb5.2 c6.4 f6.4 | e6.8 c6.8 | d6.6 c6.2 bb5.4 g5.4 | c6.16'),
                'B': dict(chords='Dm Am Bb F Gm Dm C7 C', mel=
        'f5.4 a5.4 d6.8 | c6.4 a5.4 e5.8 | f5.4 bb5.4 d6.6 c6.2 | c6.8 a5.8 |'
        'bb5.4 d6.4 g6.6 f6.2 | f6.8 d6.8 | e6.4 c6.4 g5.4 bb5.4 | a5.8 g5.8')}),
 dict(file='01', title='Bright Morning', tempo=128, key='G', mode='major', style='bounce', form=FORM,
      sections={'A': dict(chords='G D Em C G D C D', mel=
        'g5.2 b5.2 d6.4 b5.2 g5.2 a5.4 | a5.2 f#5.2 d5.4 f#5.4 a5.4 | b5.2 g5.2 e5.4 g5.2 b5.2 e6.4 | e6.4 d6.2 c6.2 g5.8 |'
        'g5.2 b5.2 d6.4 g6.4 f#6.2 e6.2 | d6.4 a5.4 f#5.4 d5.4 | e5.2 g5.2 c6.4 e6.2 d6.2 c6.4 | a5.6 b5.2 a5.8'),
                'B': dict(chords='C D Bm Em Am D G G', mel=
        'e6.4 c6.2 e6.2 g6.8 | f#6.4 d6.2 f#6.2 a6.8 | f#6.4 d6.4 b5.8 | g5.2 a5.2 b5.4 e6.8 |'
        'c6.4 a5.4 e5.4 a5.4 | f#5.2 a5.2 d6.4 c6.4 a5.4 | b5.4 g5.4 d5.4 g5.4 | g5.12 r.4')}),
 dict(file='02', title='Cog Shuffle', tempo=112, key='D', mode='minor', style='swing', form=FORM, swing=2,
      insts={'lead': dict(wave='saw', cutoff=2800, fenv=1800, fdecay=0.15, gain=0.15, duty=0.5), 'bass': dict(wave='tri', cutoff=18000, fenv=0, sub=0.2, gain=0.3)},
      sections={'A': dict(chords='Dm Gm C7 F Bb Gm6 A A7', mel=
        'd5.3 f5.1 a5.4 d6.4 a5.4 | bb5.3 a5.1 g5.4 d5.8 | e5.3 g5.1 c6.4 bb5.4 g5.4 | a5.12 r.4 |'
        'f5.3 g5.1 bb5.4 d6.4 f6.4 | e6.4 d6.4 bb5.8 | c#6.4 e6.4 a5.4 c#6.4 | e6.8 r.8'),
                'B': dict(chords='Gm Dm Gm A Bb F Gm A', mel=
        'g5.4 bb5.4 d6.6 c6.2 | a5.4 f5.4 d5.8 | g5.2 a5.2 bb5.4 g5.4 bb5.4 | a5.8 e5.8 |'
        'f5.4 bb5.4 d6.4 bb5.4 | c6.4 a5.4 f5.8 | g5.4 bb5.4 e6.4 d6.4 | c#6.8 a5.8')}),
 dict(file='03', title='Ice Palace', tempo=100, key='A', mode='minor', style='waltz', form=FORM, bar=12, echo=1.0, feedback=0.4,
      insts={'lead': dict(wave='sine', mix2=0.45, oct2=1, detune=5, gain=0.2, d=0.5, s=0.35, verb=0.45, vib=0.08, mono=0),
             'arp': dict(wave='sine', mix2=0.3, oct2=2, gain=0.05, d=0.25, verb=0.4)},
      sections={'A': dict(chords='Am Am F F Dm E Am E', mel=
        'e5.4 a5.4 c6.4 | b5.8 a5.4 | c6.4 a5.4 f5.4 | a5.12 | d6.4 c6.4 a5.4 | g#5.8 b5.4 | c6.4 b5.4 a5.4 | e5.12'),
                'B': dict(chords='C G Am Em F C Dm E', mel=
        'e6.4 g6.4 e6.4 | d6.8 b5.4 | c6.4 e6.4 a6.4 | g6.8 e6.4 | f6.4 e6.4 c6.4 | e6.8 g5.4 | f5.4 a5.4 d6.4 | b5.8 g#5.4')}),
 dict(file='04', title='Conveyor', tempo=136, key='E', mode='minor', style='drive', form=FORM,
      insts={'lead': dict(duty=0.5, cutoff=4000, gain=0.17)},
      sections={'A': dict(chords='Em C D Em Em C D B', mel=
        'e5.2 e5.2 g5.2 b5.4 a5.2 g5.2 f#5.2 | e5.4 g5.4 c6.8 | d6.2 c6.2 b5.2 a5.4 f#5.2 d5.4 | e5.12 r.4 |'
        'b5.2 b5.2 e6.4 d6.2 b5.2 g5.4 | c6.2 b5.2 a5.4 e5.8 | f#5.2 a5.2 d6.4 c6.2 a5.2 f#5.4 | d#6.8 b5.8'),
                'B': dict(chords='Am Em C D Am Em B B', mel=
        'a5.4 c6.4 e6.4 a6.4 | g6.4 e6.4 b5.8 | c6.2 e6.2 g6.4 e6.4 c6.4 | d6.4 f#6.4 a6.8 |'
        'a6.4 e6.4 c6.4 a5.4 | b5.4 g5.4 e5.8 | f#5.4 b5.4 d#6.4 f#6.4 | b6.8 f#6.8')}),
 dict(file='05', title='Sunny Puzzle', tempo=120, key='F', mode='major', style='bounce', form=FORM,
      insts={'lead': dict(duty=0.125, gain=0.2)},
      sections={'A': dict(chords='F Dm Bb C F Am Bb C', mel=
        'c6.4 a5.2 f5.2 a5.4 c6.4 | d6.4 a5.4 f5.8 | d6.4 bb5.2 f5.2 bb5.4 d6.4 | c6.6 bb5.2 g5.8 |'
        'a5.4 c6.4 f6.4 e6.2 d6.2 | c6.4 e5.4 a5.8 | bb5.2 c6.2 d6.4 f6.4 d6.4 | e6.12 r.4'),
                'B': dict(chords='Bb C Am Dm Gm C F F', mel=
        'f6.4 d6.4 bb5.8 | g5.2 a5.2 bb5.4 c6.8 | e6.4 c6.4 a5.8 | f5.2 g5.2 a5.4 d6.8 |'
        'd6.4 bb5.4 g5.4 bb5.4 | c6.4 e6.4 g6.4 e6.4 | f6.8 c6.8 | a5.12 r.4')}),
 dict(file='06', title='Night Lab', tempo=96, key='C', mode='minor', style='mystery', form=FORM, echo=1.5, feedback=0.45,
      insts={'lead': dict(wave='saw', mix2=0.6, detune=10, cutoff=1600, fenv=900, fdecay=0.3, gain=0.13, verb=0.4), 'pad': dict(gain=0.06)},
      sections={'A': dict(chords='Cm Ab Fm G Cm Ab Bb G', mel=
        'c5.6 eb5.2 g5.8 | ab5.6 g5.2 eb5.8 | f5.4 ab5.4 c6.4 f5.4 | g5.8 b4.8 |'
        'c5.4 g5.4 eb6.8 | c6.6 bb5.2 ab5.8 | bb5.4 d6.4 f6.4 d6.4 | b5.12 r.4'),
                'B': dict(chords='Fm Cm Ab Eb Fm Ab G G', mel=
        'ab5.4 c6.4 f6.8 | eb6.6 d6.2 c6.8 | c6.4 eb6.4 ab6.8 | g6.6 f6.2 eb6.8 |'
        'f6.4 ab6.4 c6.4 ab5.4 | eb6.6 c6.2 ab5.8 | g5.4 b5.4 d6.4 f6.4 | g6.8 d6.8')}),
 dict(file='07', title='Pocket Rocket', tempo=150, key='Bb', mode='major', style='drive', form=FORM,
      sections={'A': dict(chords='Bb F Gm Eb Bb F Eb F', mel=
        'f5.2 bb5.2 d6.2 f6.2 d6.4 bb5.4 | c6.2 a5.2 f5.4 c6.4 a5.4 | bb5.2 d6.2 g6.4 f6.2 d6.2 bb5.4 | g5.4 bb5.4 eb6.8 |'
        'd6.2 f6.2 bb6.4 a6.2 f6.2 d6.4 | c6.4 f6.4 a5.8 | g5.2 bb5.2 eb6.4 g6.4 eb6.4 | f6.8 c6.8'),
                'B': dict(chords='Eb F Dm Gm Cm F Bb F', mel=
        'g6.4 eb6.4 bb5.8 | a5.4 c6.4 f6.8 | f6.4 d6.4 a5.8 | bb5.4 d6.4 g6.8 |'
        'eb6.4 c6.4 g5.4 eb6.4 | f6.4 c6.4 a5.4 c6.4 | d6.4 f6.4 bb6.8 | a6.8 f6.8')}),
 dict(file='08', title='Tide Pool', tempo=104, key='Eb', mode='major', style='latin', form=FORM,
      insts={'lead': dict(wave='tri', mix2=0.3, oct2=1, gain=0.24, vib=0.1), 'bass': dict(wave='tri', cutoff=18000, fenv=0, sub=0.3, gain=0.3)},
      sections={'A': dict(chords='Eb Cm Ab Bb Eb Cm Ab Bb', mel=
        'g5.3 bb5.3 eb6.2 d6.4 bb5.4 | g5.3 c6.3 eb6.2 c6.8 | ab5.3 c6.3 eb6.2 f6.4 eb6.4 | d6.6 bb5.2 f5.8 |'
        'g5.3 bb5.3 eb6.2 g6.4 f6.4 | eb6.3 c6.3 g5.2 c6.8 | c6.3 eb6.3 ab6.2 g6.4 f6.4 | f6.12 r.4'),
                'B': dict(chords='Ab Bb Gm Cm Fm Bb Eb Bb', mel=
        'c6.4 eb6.4 ab6.8 | bb6.4 f6.4 d6.8 | d6.4 bb5.4 g5.8 | eb6.3 d6.3 c6.2 g5.8 |'
        'ab5.4 c6.4 f6.4 ab6.4 | f6.4 d6.4 bb5.8 | g5.3 bb5.3 eb6.2 g6.8 | f6.16')}),
 dict(file='09', title='Bug Hunt', tempo=124, key='G', mode='minor', style='quirky', form=FORM,
      insts={'lead': dict(duty=0.125, d=0.1, s=0.3, r=0.05, gain=0.22, vib=0.0)},
      sections={'A': dict(chords='Gm Gm Cm D Gm Eb Cm D', mel=
        'g5.2 r.2 bb5.2 r.2 d6.2 c6.2 bb5.2 a5.2 | g5.2 r.2 d5.2 r.2 g5.8 | c6.2 r.2 eb6.2 r.2 g6.2 f6.2 eb6.2 d6.2 | f#5.4 a5.4 d6.8 |'
        'g5.2 a5.2 bb5.2 d6.2 g6.4 f6.4 | eb6.2 d6.2 bb5.2 g5.2 eb5.8 | c6.2 eb6.2 g6.2 eb6.2 c6.4 a5.4 | f#5.8 d5.8'),
                'B': dict(chords='Eb F Bb Gm Cm D Gm D', mel=
        'g5.4 bb5.4 eb6.8 | a5.4 c6.4 f6.8 | f6.2 r.2 d6.2 r.2 bb5.8 | d6.2 r.2 bb5.2 r.2 g5.8 |'
        'eb6.4 g6.4 c6.4 eb6.4 | d6.4 c6.4 a5.4 f#5.4 | g5.4 bb5.4 d6.4 g6.4 | a6.8 f#6.8')}),
 dict(file='10', title='Keystone', tempo=132, key='D', mode='major', style='anthem', form=FORM,
      insts={'lead': dict(wave='saw', mix2=0.5, detune=6, cutoff=3500, fenv=1200, gain=0.14)},
      sections={'A': dict(chords='D A Bm G D A G A', mel=
        'f#5.4 a5.4 d6.6 c#6.2 | e6.4 c#6.4 a5.8 | b5.4 d6.4 f#6.6 e6.2 | d6.4 b5.4 g5.8 |'
        'a5.4 d6.4 f#6.4 a6.4 | g6.6 f#6.2 e6.8 | d6.4 b5.4 g5.4 b5.4 | c#6.12 r.4'),
                'B': dict(chords='G A F#m Bm Em A D A', mel=
        'b5.2 d6.2 g6.4 f#6.4 d6.4 | c#6.2 e6.2 a6.4 g6.4 e6.4 | f#6.4 c#6.4 a5.8 | b5.4 d6.4 f#6.8 |'
        'g6.4 e6.4 b5.4 g5.4 | a5.4 c#6.4 e6.4 g6.4 | f#6.8 d6.8 | e6.12 r.4')}),
 dict(file='11', title='Clockwork', tempo=116, key='A', mode='minor', style='clock', form=FORM,
      insts={'lead': dict(duty=0.25, gain=0.19)},
      sections={'A': dict(chords='Am G F E Am G F E', mel=
        'a5.4 e6.4 d6.2 c6.2 b5.4 | g5.4 d6.4 b5.8 | a5.2 c6.2 f6.4 e6.2 d6.2 c6.4 | b5.6 g#5.2 e5.8 |'
        'a5.4 c6.4 e6.4 a6.4 | g6.4 f6.2 e6.2 d6.8 | c6.2 d6.2 c6.2 a5.2 f5.8 | g#5.12 r.4'),
                'B': dict(chords='Dm Am Dm E F C Dm E', mel=
        'f5.4 a5.4 d6.4 f6.4 | e6.6 c6.2 a5.8 | d6.4 f6.4 a6.6 f6.2 | g#6.8 e6.8 |'
        'a6.4 f6.4 c6.8 | g6.4 e6.4 c6.8 | d6.2 e6.2 f6.4 d6.4 a5.4 | b5.8 e6.8')}),
 dict(file='12', title='Lava Run', tempo=144, key='E', mode='minor', style='drive', form=FORM,
      insts={'lead': dict(wave='saw', mix2=0.5, detune=9, cutoff=3000, fenv=2000, fdecay=0.12, gain=0.13),
             'bass': dict(cutoff=900, res=0.35)},
      sections={'A': dict(chords='Em Em C D Em Em C B', mel=
        'e6.2 b5.2 g5.2 b5.2 e6.4 f#6.4 | g6.2 f#6.2 e6.2 d6.2 b5.8 | c6.2 e6.2 g6.4 e6.2 c6.2 g5.4 | d6.2 f#6.2 a6.4 f#6.4 d6.4 |'
        'e6.2 g6.2 b6.4 a6.2 g6.2 f#6.4 | g6.4 e6.4 b5.8 | c6.4 g6.4 e6.4 c6.4 | b5.4 d#6.4 f#6.8'),
                'B': dict(chords='Am C D Em Am C B B', mel=
        'a5.4 c6.4 e6.4 a6.4 | g6.4 e6.4 c6.8 | f#6.4 d6.4 a5.4 d6.4 | e6.8 b5.8 |'
        'c6.2 e6.2 a6.4 g6.2 e6.2 c6.4 | e6.2 g6.2 c7.4 b6.2 g6.2 e6.4 | d#6.4 f#6.4 b6.8 | a6.4 f#6.4 d#6.8')}),
 dict(file='13', title='Last Stretch', tempo=126, key='C', mode='major', style='bounce', form=FORM,
      insts={'lead': dict(duty=0.3, gain=0.2)},
      sections={'A': dict(chords='Am F C G Am F C G', mel=
        'e5.4 a5.4 c6.4 b5.4 | a5.4 f5.4 c6.8 | g5.4 c6.4 e6.4 d6.4 | d6.8 b5.8 |'
        'a5.4 c6.4 e6.4 g6.4 | f6.4 e6.4 c6.8 | e6.4 g6.4 c7.4 b6.4 | b6.8 g6.8'),
                'B': dict(chords='F G Em Am Dm G C G', mel=
        'a6.4 f6.4 c6.8 | b5.4 d6.4 g6.8 | g6.4 e6.4 b5.8 | c6.4 e6.4 a6.8 |'
        'f6.4 d6.4 a5.4 d6.4 | g6.4 f6.4 d6.4 b5.4 | c6.8 e6.4 g6.4 | g6.12 r.4')}),
]

def main():
    os.makedirs(OUT, exist_ok=True)
    for s in SONGS:
        path, secs = write_song(s)
        print(f"{os.path.basename(path):18s} {s['title']:16s} {s['tempo']} bpm  {secs:5.1f} s")

if __name__ == '__main__':
    main()
