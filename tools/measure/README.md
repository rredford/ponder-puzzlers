# Off-map behaviour measurements

Black-box experiments on the original cartridge, run in a Lynx emulator (not included; the scripts expect
the verification setup described in spec doc 10: an emulator library, a power-on state snapshot and the
user's own cartridge image). Each experiment builds a small level in the cartridge's level format, injects
it as level 1, optionally sets a byte of game state after the level has started, runs a few ticks and records
what is *observed* (object positions, map cells, crash or not). No program bytes are read.

| Script | Measures |
|---|---|
| `measure.py` | entry by type/direction for every tile code, slide/ice flags, stray-type steps, effect frames, arrival outcomes, object references used as tiles, display effects |
| `fit_odd.py` | fits a handler model (stop / keep moving / redirect, leave mask) to the codes that do not crash |
| `gen_stray.py`, `gen_objref.py` | turn the measurements into `src/core/stray_tables.inc` and check the model reproduces every measurement |
| `cxx_lock.py`, `cxx_suite.py` | lock-step the C++ engine (`levelpack raw`) against the original on ~3000 scenarios |
| `emu_only.py` | outcome of every solution on the original (levels injected; no spec-engine lock-step) |
| `check_slot0.py`, `check_stray_on_real_tiles.py`, `check_boots_on_move_on_codes.py` | lock-step regression checks: any type in slot 0 on every tile; stray types on every tile; boots on the three "move on at once" codes |

## Oddity 2 grouped sweep (odd tile codes drawn on screen)
- `oddgroups.py` — one code per group (grouped by where its drawing write lands), Chip idle: crash and RAM diffs vs a floor control.
- `oddgroups2.py` — Chip walking, ball bouncing; first game-state divergence ignoring the 4 written bytes.
- `oddgroups3.py` — event course (chip, key, skates, buttons, hint, exit / water); crash or same end state.
Results are summarised in doc 04 §4.4 ("Odd tile codes, grouped").
- `gen_draw.py` (+ `pokedelay.py`) — generates `src/core/draw_tables.inc` (per-code write address and kind; code 6E crash class per x value).
- `drawtest.py N SEED` — random lock-step accuracy test of the drawing rules, engine with and without its draw pass.
