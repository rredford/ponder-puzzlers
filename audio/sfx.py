#!/usr/bin/env python3
"""Newly designed sound effects for the 18 effect slots of spec doc 08 §3 -> assets/audio/sfx_XX.song.
All sounds are original designs made with the game's own synthesizer (src/audio/synth.cpp);
nothing is taken from the cartridge. Timing: tempo 600, 4 ticks per beat -> 1 tick = 25 ms."""
import os
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'audio')

HEAD = "tempo 600\ntpb 4\necho 0.5 0.2\n"

def sfx(name, insts, notes, length=None, loop=None):
    lines = [f"name {name}", HEAD.strip()]
    for nm, params in insts.items():
        lines.append(f"inst {nm} " + " ".join(f"{k}={v}" for k, v in params.items()))
    end = 0
    for n in notes:
        t, inst, p, ln, v = n[:5]
        extra = f" to={n[5]}" if len(n) > 5 else ""
        lines.append(f"n {t} {inst} {p} {ln} {v}{extra}")
        end = max(end, t + ln)
    lines.append(f"length {length or end}")
    if loop is not None: lines.append(f"loop {loop}")
    return "\n".join(lines) + "\n"

BELL = dict(wave='sine', mix2=0.35, oct2=2, detune=4, a=0.002, d=0.25, s=0.0, r=0.2, gain=0.32, verb=0.35, delay=0.15)
BLIP = dict(wave='pulse', duty=0.25, a=0.002, d=0.08, s=0.3, r=0.06, gain=0.22, cutoff=7000, verb=0.2)
NOISE = dict(wave='noise', noiserate=40, a=0.002, d=0.12, s=0.0, r=0.05, gain=0.30, cutoff=4000)

EFFECTS = {
    # 00 pick up key / boot / chip, any button: a quick rising two-note chime with a sparkle on top
    0x00: ("pickup", {'bell': BELL, 'spark': dict(BLIP, duty=0.125, gain=0.12, d=0.05, s=0.0)},
           [(0, 'bell', 88, 2, 0.8), (2, 'bell', 95, 6, 1.0), (2, 'spark', 107, 1, 0.6), (3, 'spark', 112, 1, 0.4)]),
    # 01 recessed wall rises: a low square swept upward with a thump of noise
    0x01: ("popup", {'sq': dict(wave='pulse', duty=0.5, a=0.002, d=0.2, s=0.2, r=0.08, gain=0.25, cutoff=2500),
                     'thump': dict(NOISE, cutoff=900, d=0.08)},
           [(0, 'sq', 40, 5, 1.0, 55), (0, 'thump', 60, 2, 0.9)]),
    # 02 thief: a teasing "wah-wah-waaah" falling minor third pattern
    0x02: ("thief", {'wah': dict(wave='saw', a=0.01, d=0.15, s=0.7, r=0.12, gain=0.22, cutoff=600, fenv=2400, fdecay=0.12, vib=0.2, vibrate=7, vibdelay=0.08)},
           [(0, 'wah', 67, 4, 0.9), (5, 'wah', 64, 4, 0.9), (10, 'wah', 60, 10, 1.0, 58)]),
    # 03 exit / teleport: a shimmering upward sweep of fast arpeggio notes
    0x03: ("warp", {'arp': dict(BLIP, duty=0.3, gain=0.18, delay=0.35, verb=0.4),
                    'whoosh': dict(NOISE, gain=0.12, cutoff=1200, fenv=6000, fdecay=0.3, d=0.4, a=0.05)},
           [(i, 'arp', 72 + [0, 4, 7, 12][i % 4] + 12 * (i // 4), 1, 0.9 - i * 0.04) for i in range(12)]
           + [(0, 'whoosh', 80, 12, 0.8)]),
    # 04 (unused by the game logic): a soft menu blip
    0x04: ("blip", {'b': BLIP}, [(0, 'b', 84, 2, 0.8)]),
    # 05 door / socket opens, cloning: a mechanical clack and a short falling slide
    0x05: ("door", {'clack': dict(wave='metal', noiserate=6, a=0.001, d=0.05, s=0.0, r=0.03, gain=0.25, cutoff=5000),
                    'slide': dict(wave='pulse', duty=0.3, a=0.002, d=0.1, s=0.5, r=0.05, gain=0.18, cutoff=3000)},
           [(0, 'clack', 70, 1, 1.0), (1, 'slide', 64, 5, 0.8, 52)]),
    # 06 ice slide (looping): a soft airy hiss with a gentle glassy shimmer
    0x06: ("ice-loop", {'hiss': dict(wave='noise', noiserate=60, a=0.05, d=0.1, s=1.0, r=0.1, gain=0.08, cutoff=3500, hp=900),
                        'glass': dict(wave='sine', mix2=0.4, oct2=1, detune=7, a=0.02, d=0.3, s=0.0, r=0.2, gain=0.05, verb=0.4)},
           [(0, 'hiss', 80, 16, 1.0), (0, 'glass', 100, 6, 0.7), (8, 'glass', 103, 6, 0.6)], 16, 0),
    # 07 boots in use (skates on ice, suction on force floor): two crisp ticks
    0x07: ("boots", {'tick': dict(BLIP, duty=0.125, d=0.03, s=0.0, gain=0.18)},
           [(0, 'tick', 96, 1, 0.9), (2, 'tick', 91, 1, 0.7)]),
    # 08 bump / something enters a trap: a short muffled thud
    0x08: ("bump", {'thud': dict(wave='sine', pslide=12, pdecay=0.02, a=0.001, d=0.08, s=0.0, r=0.03, gain=0.45),
                    'tap': dict(NOISE, cutoff=700, d=0.03, gain=0.15)},
           [(0, 'thud', 43, 2, 1.0), (0, 'tap', 60, 1, 0.7)]),
    # 09 death: a falling three-step tumble into a noisy crash
    0x09: ("death", {'fall': dict(wave='pulse', duty=0.5, a=0.002, d=0.2, s=0.5, r=0.1, gain=0.22, cutoff=3000, vib=0.3, vibrate=9, vibdelay=0.0),
                     'crash': dict(NOISE, noiserate=20, d=0.5, gain=0.3, cutoff=2500, fenv=4000, fdecay=0.15, verb=0.3)},
           [(0, 'fall', 72, 3, 1.0, 68), (3, 'fall', 66, 3, 1.0, 62), (6, 'fall', 60, 8, 1.0, 40), (6, 'crash', 60, 12, 1.0)]),
    # 0A (unused): a low "boop"
    0x0A: ("boop-low", {'b': dict(BLIP, duty=0.5, cutoff=2000)}, [(0, 'b', 60, 2, 0.8, 57)]),
    # 0B dirt / fake wall cleared, door opened (after 05): a soft brushing puff
    0x0B: ("brush", {'puff': dict(NOISE, noiserate=30, a=0.01, d=0.1, gain=0.16, cutoff=1800, hp=300)},
           [(0, 'puff', 70, 3, 1.0)]),
    # 0C splash (drowning, block into water, ice-corner deflection): a wet burst and a couple of bubbles
    0x0C: ("splash", {'water': dict(NOISE, noiserate=25, a=0.002, d=0.25, gain=0.26, cutoff=600, fenv=5000, fdecay=0.08),
                      'bubble': dict(wave='sine', a=0.002, d=0.06, s=0.0, r=0.03, gain=0.16)},
           [(0, 'water', 70, 6, 1.0), (3, 'bubble', 79, 1, 0.8, 86), (5, 'bubble', 84, 1, 0.6, 91)]),
    # 0D (unused): a high "boop"
    0x0D: ("boop-high", {'b': dict(BLIP, duty=0.5)}, [(0, 'b', 79, 2, 0.8, 84)]),
    # 0E force floor (looping): a low buzzing conveyor hum with a steady rattle
    0x0E: ("force-loop", {'hum': dict(wave='pulse', duty=0.3, pwm=0.15, pwmrate=6, a=0.04, d=0.1, s=1.0, r=0.1, gain=0.07, cutoff=900),
                          'rattle': dict(wave='metal', noiserate=3, a=0.002, d=0.03, s=0.0, r=0.02, gain=0.05, cutoff=3000)},
           [(0, 'hum', 38, 8, 1.0), (0, 'rattle', 60, 1, 0.8), (2, 'rattle', 60, 1, 0.5), (4, 'rattle', 60, 1, 0.8), (6, 'rattle', 60, 1, 0.5)],
           8, 0),
    # 0F pushing a block: a gritty low scrape
    0x0F: ("push", {'scrape': dict(wave='noise', noiserate=10, a=0.01, d=0.1, s=0.3, r=0.05, gain=0.22, cutoff=800),
                    'groan': dict(wave='saw', a=0.01, d=0.1, s=0.5, r=0.05, gain=0.08, cutoff=400)},
           [(0, 'scrape', 50, 4, 1.0), (0, 'groan', 33, 4, 1.0, 31)]),
    # 10 walking into fire with fire boots: a fizzy crackle
    0x10: ("fire", {'crackle': dict(wave='metal', noiserate=12, a=0.002, d=0.06, s=0.0, r=0.03, gain=0.16, cutoff=6000, hp=600),
                    'roar': dict(NOISE, noiserate=20, d=0.2, gain=0.1, cutoff=1500)},
           [(0, 'roar', 60, 5, 1.0), (0, 'crackle', 72, 1, 0.9), (2, 'crackle', 77, 1, 0.7), (3, 'crackle', 69, 1, 0.8)]),
    # 11 swimming (entering water with flippers): a gentle rising gurgle
    0x11: ("swim", {'gurgle': dict(wave='sine', mix2=0.2, oct2=1, a=0.005, d=0.08, s=0.3, r=0.05, gain=0.2, vib=0.6, vibrate=18, vibdelay=0.0, verb=0.2)},
           [(0, 'gurgle', 67, 2, 0.9, 74), (2, 'gurgle', 71, 3, 0.8, 79)]),
}

# loudness trim per effect (multiplies every instrument gain), set by ear-free metering with audiorender
LEVEL = {0x01: 1.4, 0x02: 1.8, 0x05: 1.6, 0x06: 2.0, 0x07: 2.2, 0x0B: 3.5, 0x0C: 1.8, 0x0E: 1.8, 0x0F: 2.0, 0x10: 2.8, 0x11: 2.0}

def main():
    os.makedirs(OUT, exist_ok=True)
    for sid, spec in EFFECTS.items():
        name, insts, notes = spec[:3]
        insts = {k: dict(v, gain=round(v.get('gain', 0.5) * LEVEL.get(sid, 1.0), 3)) for k, v in insts.items()}
        length = spec[3] if len(spec) > 3 else None
        loop = spec[4] if len(spec) > 4 else None
        with open(os.path.join(OUT, 'sfx_%02X.song' % sid), 'w') as f:
            f.write(f"# sound effect {sid:02X}: {name} (original design)\n" + sfx(name, insts, notes, length, loop))
    print('effects:', len(EFFECTS))

if __name__ == '__main__':
    main()
