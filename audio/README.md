# Audio

All music and sound effects are newly composed for Ponder Puzzlers and played by the game's own software synthesizer
(`src/audio/synth.cpp`). Nothing is taken from the cartridge. The slots and triggers follow spec doc 08:

- **18 sound effects** `assets/audio/sfx_00.song` … `sfx_11.song`, one per effect id, with the same trigger rules.
  `sfx_06` (ice) and `sfx_0E` (force floor) are looping sounds owned by the game state. Ids 04, 0A and 0D are not
  triggered by the game logic and are simple blips.
- **15 music tracks**: `music_title`, `music_ending`, and 13 level tunes `music_01` … `music_13`. A level's tune
  is chosen as on the cartridge: `(3rd password letter − 'A') >> 1`. Level music restarts at each attempt.

| File | Title | Style |
|---|---|---|
| music_title | Circuit Hero | C major march, 140 bpm |
| music_ending | Homecoming | F major ballad, 92 bpm |
| music_01 | Bright Morning | G major bounce |
| music_02 | Cog Shuffle | D minor swing |
| music_03 | Ice Palace | A minor waltz, bells |
| music_04 | Conveyor | E minor drive |
| music_05 | Sunny Puzzle | F major bounce |
| music_06 | Night Lab | C minor, slow and mysterious |
| music_07 | Pocket Rocket | B♭ major, fast |
| music_08 | Tide Pool | E♭ major, Latin feel |
| music_09 | Bug Hunt | G minor, staccato |
| music_10 | Keystone | D major anthem |
| music_11 | Clockwork | A minor, ticking arpeggios |
| music_12 | Lava Run | E minor, intense |
| music_13 | Last Stretch | A minor → C major, hopeful |

## Regenerating

```sh
python3 audio/sfx.py        # effects
python3 audio/compose.py    # music (applies the gain trims in audio/mix.json)
python3 audio/automix.py    # optional: re-measure every part and update audio/mix.json, then compose.py again
./build/audiorender assets/audio/music_01.song out.wav      # listen to one (one pass + tail)
./build/audiorender assets/audio/music_01.song out.wav 120  # 120 s, looping
```

## Song format

Plain text, one command per line, `#` comments.

```
name   Bright Morning
tempo  128            # beats per minute
tpb    12             # ticks per beat
echo   0.75 0.3       # echo time in beats, feedback
inst   lead wave=pulse duty=0.25 a=0.008 d=0.25 s=0.55 r=0.12 vib=0.12 gain=0.2 delay=0.22 verb=0.2 mono=1
n      0 lead 67 6 0.95          # tick instrument midi-note length-in-ticks velocity [to=glide-target]
length 1536           # end of the song in ticks
loop   96             # loop start tick (-1: play once)
```

Instrument parameters: `wave` (pulse saw tri sine noise metal), `duty pwm pwmrate`, second oscillator
`mix2 oct2 detune` (cents), `sub` (sine an octave down), envelope `a d s r`, low-pass `cutoff res fenv fdecay
keytrack`, high-pass `hp`, `vib vibrate vibdelay`, pitch drop `pslide pdecay`, `noiserate`, `gain pan`, effect sends
`delay verb`, and `mono` (a new note cuts the previous one).
