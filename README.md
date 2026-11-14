# Made with LLM, beware of slop. I carefully ensured it works well, but be aware.

# Ponder Puzzlers — a remake engine for the Atari Lynx *Chip's Challenge* cartridge

Name chosen 2026-11-01 (formerly the working title "Chiplynx"). A native Linux (C++17 + SDL2) reimplementation written from the clean-room specification in `cleanroom-spec/` (project docs 00–10). **No ROM is needed:** it ships with an original 10-level set (*Pip's First Steps*), plays any standard `.dat`/`.ccl` level set (e.g. CCLP1), and can optionally read the levels straight from your own cartridge image. All graphics and audio are new (original art, newly composed music and effects); no ROM graphics, sound or code are used or shipped.

## Status

| Part | State |
|---|---|
| Engine (`src/core`) | Complete per spec docs 02–05, including the measured off-map glitch behaviour (doc 04 §4.4). **All 148 CC1 Tile World solution replays match the original ROM's outcome and tick** (`selftest`), as do the community packs below |
| Level sources | Built-in original set · standard DAT/CCL files (`--levels`) · optional cartridge image (`--rom`) |
| ROM reader | LNX/headerless, directory, BPE decompression, level parsing, passwords |
| Front-end (`src/app`) | Title, password entry, level intro, play, pause, hint, death/finish screens, scoring, skip offer, ending; smooth scrolling (render interpolation between 20 Hz ticks) |
| Art (`art/generate.py`) | Original cartoon tiles, monsters, hero ("Pip"), effects; 48×48, procedurally drawn |
| Audio | Newly composed: 18 sound effects and 15 music tracks played by the built-in synthesizer (`src/audio`, see `audio/README.md`) |

## Build

```sh
sudo apt install build-essential cmake libsdl2-dev python3-pil python3-numpy   # Debian/Ubuntu (numpy: only for audio/automix.py)
python3 art/generate.py            # (re)generates assets/ and src/app/atlas_index.hpp
# needs the Poppins Bold font (SIL OFL): installed system-wide, Poppins-Bold.ttf in art/, or PONDER_FONT=/path/to/Poppins-Bold.ttf
cmake -S . -B build
cmake --build build -j
```

Or simply run `./build.sh` (also by double-click): it builds and starts the game. `./build.sh build` only builds, `./build.sh clean` rebuilds from scratch, `./build.sh test` runs the self-test (needs your own cartridge image at `rom/game.lnx`).

## Run

```sh
./build/ponderpuzzlers                                            # built-in set "Pip's First Steps"
./build/ponderpuzzlers --levels CCLP1.dat                         # any standard .dat level set
./build/ponderpuzzlers --rom /path/to/Chips_Challenge.lnx         # levels from your own cartridge
./build/ponderpuzzlers --levels CCLP1.dat --level 12              # jump to a level
./build/ponderpuzzlers --rom game.lnx --level 4 --replay CC1.dac.tws   # watch a Tile World solution
```

Keys: arrows / WASD move · Enter or Space confirm · P pause · R restart level · Esc title screen (Step Mode adds Space, B and Backspace, below).

Options menu: **Music** and **Sound Effects** on/off (remembered). Level music is chosen per level as on the cartridge and restarts at each attempt; the ice and force-floor sounds loop while Chip slides.

**Hacks menu** (not part of the Lynx rules; Step Mode and Helmet are remembered; the side panel shows which hacks are in use):
- **Step Mode:** the game only runs on key presses (holding a key keeps it stepping at normal speed; letting go stops at the end of the move). An arrow key plays one full move (4 ticks, longer if sliding leaves Chip between cells): Chip steps that way while monsters, ice and force floors carry on as usual. **Space** runs one tick and **B** one full move with Chip standing still (he can still be caught, slide or be pushed). **Backspace** undoes the last step, also after dying (the whole game state is restored: drownings, pick-ups, clones, the clock). R restarts the level. The tile animations pause with the game between steps.
  **Level → Show Moves…** (Ctrl+M) lists the steps of the current attempt (undo takes them back): in Tile World's letters — `U D L R` a move, `-` one tick of waiting (Space adds one `-`, B as many as the ticks it ran) — in groups of 10, with a Copy button. `levelpack steps set.dat N "MOVES"` (or `@file`; add `--helmet` and `--boots=ksfw` if those hacks were used, since they are not in the list) replays such a list with the same timing.
- **Edit Inventory…** (Ctrl+I): set the four key counts (0–255; Left/Right, Page Up/Down, or type a number) and switch each pair of boots on or off; applied with OK. In Step Mode the edit is one undo step.
- **Helmet:** a monster or block moving into Chip is stopped as by a wall instead of killing him, so Chip can be boxed in. Walking into a monster yourself still kills Chip, as do fire, water and bombs.

Menu bar: **File → Load ROM…** (Ctrl+Shift+O, `.lnx`), **File → Load Level Pack…** (Ctrl+O, `.dat` / `.ccl`), **File → Quit** (Ctrl+Q); **Level → Select Level…** (Ctrl+G: type a number, the playable range is shown below it), **Next Level** (Ctrl+N) and **Previous Level** (Ctrl+P), wrapping from the last level to the first and back. F10 opens the menus from the keyboard. File dialogs use zenity or kdialog when installed, otherwise a built-in browser (`--no-native-dialogs` forces the built-in one); the last folder is remembered.

## Level sets

DAT files use Microsoft-style tile codes; they are converted to Lynx tiles on load. Tiles that exist only in MSCC become walls. Two rules modes, chosen on the title screen (checkboxes, Up/Down or M) or with `--strict` / `--extended`; the choice is remembered:

| | **Strict LYNX ROM** (default) | **Extended LYNX mode** |
|---|---|---|
| Button → trap/cloner wiring | cartridge rule: next one in reading order | the DAT's wiring lists (as Tile World) |
| North/west thin walls | moved to the neighbour's south/east edge; dropped if it can't carry it | real north/west thin walls |
| Objects | 128 slots, like the cartridge | up to 2048 |
| Map edge | as the cartridge: no bounds check (moves wrap/alias RAM, see spec doc 04 §4.2) | solid |

Strict mode plays a DAT level exactly as the original cartridge would if the level were on it (verified by injecting the levels into the emulated original, below) — including levels whose monsters wander off the map edge and corrupt the game: what the original does with the stray bytes it then meets (odd tile codes, impossible object types, junk effect frames, corrupted button/teleport links) was **measured by black-box tests** and is built in as behaviour tables (`src/core/stray_tables.inc`, generated by the measurement scripts; spec doc 04 §4.4). No cartridge bytes are needed or shipped. Where the original crashes or hangs, the remake shows "Cartridge crash!". Where the outcome depends on memory the remake does not hold (the sound driver, the stack), it plays on and shows a desync notice instead of guessing.

```sh
./build/levelpack info CCLP1.dat [--extended]               # list levels, passwords, conversion warnings
./build/levelpack replay CCLP1.dat CCLP1-Lynx.dac.tws [--extended]   # outcome of every solution
./build/levelpack lynx CCLP1.dat outdir/                    # cartridge-format level files (strict) for testing
./build/levelpack links CCLP1.dat                           # buttons whose DAT wiring differs from the cartridge rule
./build/levelpack check assets/pip_levels.dat assets/pip_levels_moves.txt   # prove each level is solvable
./build/levelpack export game.lnx cc1-lynx.dat              # your cartridge's levels as a DAT (personal use only)
./build/levelpack verify cc1-lynx.dat CC1.dac.tws tests/oracle_cc1.tsv      # 148/148 on the exported file (levels 1-144, 146-149)
```

The built-in set is defined in `art/levels.py` (ASCII maps). Running it regenerates `assets/pip_levels.dat` (also playable in Tile World) and `src/app/builtin_levels.hpp`.

## Test

```sh
./build/selftest game.lnx                                   # ROM vectors, passwords, level 1
./build/selftest game.lnx CC1.dac.tws tests/oracle_cc1.tsv  # + 148 solution replays vs the oracle (1-144, 146-149)
```

`tests/oracle_cc1.tsv` is the outcome table from spec doc 09 §6 (original ROM behaviour).

```sh
./build/levelpack verify CCLP1.dat CCLP1-Lynx.dac.tws tests/oracle_cclp1_strict.tsv           # 149/149
./build/levelpack verify CCLP5.dat C1059-CCLP5-Lynx.dac.tws tests/oracle_cclp5_strict.tsv     # 100/100
./build/levelpack verify geo5-1.dat geo5-1-lynx.dac.tws tests/oracle_geo5_1_strict.tsv     # 9/9
./build/levelpack verify geo5-2.dat geo5-2-lynx.dac.tws tests/oracle_geo5_2_strict.tsv     # 9/9
./build/levelpack verify geo5-5.dat geo5-5.dat-lynx.dac.tws tests/oracle_geo5_5_strict.tsv # 10/10
./build/levelpack verify Joshie.dat Joshie.dat-ms.dac.tws tests/oracle_joshie_ms_strict.tsv    # 1325/1325 (MS solutions as input)
./build/levelpack verify Jacques.dat Jacques.dat-ms.dac.tws tests/oracle_jacques_ms_strict.tsv # 985/986 (986 with --link-init)
./build/levelpack verify CCLP3.dat CCLP3.tws tests/oracle_cclp3.tsv         # 149/149
./build/levelpack verify CCLP4.dat CCLP4.tws tests/oracle_cclp4.tsv         # 149/149
./build/levelpack verify CCLXP2.dat CCLXP2.tws tests/oracle_cclxp2.tsv      # 149/149
```

```sh
./build/levelpack check tests/keys256.ccl tests/keys256_moves.txt   # must report "stuck": 256 red keys wrap the count to 0, so the red door stays shut (as on the original)
```

`tests/oracle_cclp1_strict.tsv` holds the outcomes of the CCLP1 Tile World solutions on the original cartridge, with each level converted (strict mode) and injected into the emulated cartridge (spec doc 09 §7). The CCLP5 and geo5 oracles were made the same way (doc 09 §8). Several of these levels crash the original after monsters leave the map; the remake reproduces each crash on the same tick from the measured tables alone. The Joshie and Jacques oracles use MS-ruleset solutions purely as input (doc 09 §9); all of them match, including the ones where the original draws a junk object on screen (spec doc 04 §4.4). `--link-init FILE` (test only) starts replays from a given link table, as the emulated original had it.

## Layout

```
src/core/   rom.*  level.*  engine.*  tws.*  dat.*   engine library, no dependencies
src/app/    main.cpp  assets.*  ui.*            SDL2 front-end
art/        generate.py  levels.py              artwork generator, built-in level set
audio/      sfx.py  compose.py  automix.py      sound effects and music (original), mix trims
src/audio/  synth.*                             software synthesizer
assets/     atlas.rgba  font_*.rgba  pip_levels.*   generated (do not edit)
assets/audio/  sfx_XX.song  music_*.song      generated by audio/*.py
tools/      selftest.cpp  levelpack.cpp  audiorender.cpp
tests/      oracle_*.tsv (CC1, CCLP1/3/4/5, CCLXP2, geo5-1/2/5, Joshie, Jacques)  keys256.*
tools/measure/  black-box measurement scripts (need an emulator + your own ROM; not run by the build)
cleanroom-spec/ the clean-room specification (docs 00–10)
notes/      ideas.md (test notes and results)
```

## Legal notes

- No cartridge content is included. `--rom` and `levelpack export` work only from an image you supply; do not redistribute exported files. The off-map behaviour tables are measurements of what the original *does*, not copies of its data.
- The built-in levels are original.
- Artwork is original (drawn by `art/generate.py`). The hero is an original character, not Chip McCallahan.
- UI font: Poppins Bold (SIL Open Font License 1.1), baked into `assets/font_*.rgba`.
- "Chip's Challenge" is a trademark of its owner. This project is called "Ponder Puzzlers" and is not affiliated with it.
