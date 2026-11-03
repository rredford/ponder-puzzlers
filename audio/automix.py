#!/usr/bin/env python3
"""Mix-by-meter: renders every instrument of every song on its own (build/audiorender), measures its
loudness while it is playing, and writes per-song gain trims to audio/mix.json so each part sits at a
target level relative to the melody. Run compose.py, then this, then compose.py again (it applies mix.json)."""
import json, math, os, re, subprocess, sys, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER = os.path.join(ROOT, 'build', 'audiorender')
TARGET = {'lead': 0, 'bass': -3, 'kick': -4, 'snare': -8, 'snrtone': -14, 'hat': -16, 'ohat': -18, 'tick': -16,
          'shaker': -18, 'pad': -12, 'arp': -11, 'lead2': -8, 'bell': -10}

def active_db(path):
    w = wave.open(path); d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    d = d.reshape(-1, 2).mean(axis=1)
    win = 2400
    n = len(d) // win
    if n == 0: return -120
    e = (d[:n * win].reshape(n, win) ** 2).mean(axis=1)
    db = 10 * np.log10(e + 1e-12)
    act = db[db > db.max() - 30]
    return float(10 * math.log10(np.mean(10 ** (act / 10)) + 1e-12))

def measure(song_path):
    lines = open(song_path).read().split('\n')
    insts = [l.split()[1] for l in lines if l.startswith('inst ')]
    out = {}
    for ins in insts:
        keep = [l for l in lines if not l.startswith('n ') or l.split()[2] == ins]
        keep = ['loop -1' if l.startswith('loop') else l for l in keep]
        tmp = '/tmp/automix_stem.song'
        open(tmp, 'w').write('\n'.join(keep))
        subprocess.run([RENDER, tmp, '/tmp/automix_stem.wav'], check=True, capture_output=True)
        out[ins] = active_db('/tmp/automix_stem.wav')
    return out

def main():
    mixf = os.path.join(ROOT, 'audio', 'mix.json')
    mix = json.load(open(mixf)) if os.path.exists(mixf) else {}
    adir = os.path.join(ROOT, 'assets', 'audio')
    for fn in sorted(os.listdir(adir)):
        if not fn.startswith('music_'): continue
        key = fn[len('music_'):-len('.song')]
        lv = measure(os.path.join(adir, fn))
        ref = lv['lead']
        trims = mix.get(key, {})
        report = []
        for ins, db in lv.items():
            want = ref + TARGET.get(ins, -12)
            t = trims.get(ins, 1.0) * 10 ** ((want - db) / 20)
            trims[ins] = round(min(6.0, max(0.15, t)), 3)
            report.append(f"{ins} {db - ref:+.1f}")
        subprocess.run([RENDER, os.path.join(adir, fn), '/tmp/automix_full.wav'], check=True, capture_output=True)
        full = active_db('/tmp/automix_full.wav')
        trims['_master'] = round(min(5.0, max(0.3, trims.get('_master', 1.0) * 10 ** ((-18 - full) / 20))), 3)
        report.append(f"| mix {full:.1f} dBFS")
        mix[key] = trims
        print(f"{key:7s} " + "  ".join(report))
    json.dump(mix, open(mixf, 'w'), indent=1, sort_keys=True)

if __name__ == '__main__':
    main()
