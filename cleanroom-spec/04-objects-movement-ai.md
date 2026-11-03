# 04 — Objects, Movement Engine & Creature AI

This document specifies the simulation precisely enough to reproduce the original's behaviour tick-for-tick, including its quirks. Pseudocode here is newly written to describe behaviour.

## 1. World state

- `map[1024]` — tile code (`< 0x80`) or object reference `0x80 | slot`.
- 128 object slots, each: `state` (doc 02 §3), `x`, `y` (1/8-tile units, 8-bit — see §4.2), `under` (the tile code beneath the object).
- Slot 0 is Chip. Slots are fixed: an object keeps its slot for life; freed slots are reused by the cloner (lowest free slot ≥ 1).
- Player inventory: `keys[4]` (red, blue, yellow, green; 8-bit counts 0–255 — the 256th key of a colour wraps the count to 0, verified in emulation; some community levels rely on this), `boots` = {skates, suction, fire, flippers} (flags).
- Level flags: `chips_left` (16-bit), `finished`, `death_reason` (none / time-out / killed), `tank_reverse` (0–3), toggle-swap state, socket open/closed.
- Global (never reset after power-on, start at 0): `tick` (8-bit, increments each running tick), `R` (random force-floor counter, 2 bits).
- `rng` — the 16-bit generator of doc 02 §6.1; **reset to (0,0) at the start of every level attempt.**
- `probe` — a mode flag used during move tests: `0` = real move, `1` = decision probe, `0x80` = teleport-exit probe.

An object is **aligned** when `x % 8 == 0 and y % 8 == 0`; its cell is `(y/8)*32 + x/8` (floor division).

**Alive** = state ≠ 0 and dying flag clear.

## 2. Tick structure

When the game is *running* (not waiting for first input, not paused, Chip not dead, level not finished — doc 05), each tick performs, in order:

1. `tick += 1` (mod 256).
2. **Decision phase** (`probe = 1`): visit slots **127, 126, …, 1, then 0**.
   - For slots ≥ 1: skip if `state == 0` or the moving flag is set.
   - If the dying flag is set: on **odd** ticks advance the effect animation (§8); when it ends, remove the object (§8). Done.
   - Otherwise, if aligned, dispatch on the slot's **type** (bits 5–2 of its state): type 1 runs Chip's **input handler** (doc 05 §2), which always acts on slot 0; types 2–11 run that type's **AI** (§9) on this slot (type 7, the block, does nothing); type 0 does nothing. Normally only slot 0 has type 1, but stray bytes written off the map edge (§4.2) can give any slot — slot 0 included — any type. Type 13 advances the RNG once (`next()`, doc 02 §6.1) and does nothing else; types 12, 14 and 15 jump to undefined code (crash).
3. **Movement phase** (`probe = 0`): for slots **127 down to 0**: `advance(slot)` (§4).
4. **Clock** (doc 05 §4).

## 3. Move test — `test_move(i)`

Returns PASSABLE or BLOCKED for object `i` moving one cell in its current direction `d` from its (aligned) cell `c`. It may have side effects.

```
test_move(i):
  if dying(i): return BLOCKED
  cm = class_mask(type(i), d)                       # doc 03 §1
  if leave_mask(under[i]) & dirbit(d): return BLOCKED
  t = neighbour(c, d)                               # N:-32  E:+1  S:+32  W:-1
  v = map[t]
  if v is a tile:
      if SPECIAL(v): return special_bump(i, v, t)
      return BLOCKED if entry_mask(v) & cm else PASSABLE
  j = v & 0x7F                                      # cell occupied by object j
  if entry_mask(under[j]) & cm: return BLOCKED      # must be able to enter the tile under j
  if i != 0:                                        # mover is a monster or block
      if dying(j):                                  # stale effect in the way: erase it
          map[t] = under[j]; state[j] = 0
          return test_move(i)                       # re-test from the start
      if j != 0: return BLOCKED
      kill_chip_by(i)                               # monster/block runs into Chip
      return BLOCKED
  else:                                             # mover is Chip
      if dying(j): return BLOCKED
      if type(j) == BLOCK: return push_block(j)
      if type(j) == CHIP: return PASSABLE           # (cannot happen in practice)
      kill_chip_by(j)                               # Chip runs into a monster
      return BLOCKED
```

`kill_chip_by(k)`: Chip's state becomes the *Chip-death* effect (state `0x46`); **object k also becomes a Chip-death effect** (`0x46`) at its own position; `death_reason = killed`; sfx 09.

`special_bump(i, v, t)` — doors `1A–1D`, hidden wall `26`, invisible wall `27`, real blue wall `32`:
```
  if i != 0: return BLOCKED
  if probe == 1: return BLOCKED                      # Chip's decision probe never opens doors
  if v is a door of colour k:
      if keys[k] == 0: return BLOCKED
      if probe == 0 and k != GREEN: keys[k] -= 1
      return PASSABLE
  if v in {26, 32}: map[t] = WALL (01)               # wall becomes visible
  return BLOCKED
```

`push_block(j)` (Chip moving into a block):
```
  pushing_pose = true                               # selects Chip's pushing animation
  if not aligned(j) or under[j] == CLONER: return BLOCKED
  state[j] = BLOCK, direction = Chip's direction, moving flag set
  if test_move(j) is BLOCKED: return BLOCKED
  sfx 0F
  if probe == 1: return BLOCKED                     # quirk: see note
  advance(j)                                        # block moves immediately (probe 0 or 0x80)
  return PASSABLE
```
*Quirk:* during Chip's decision probe the block is already given a moving flag and direction, even though the probe reports BLOCKED. Because the block's slot (≥1) is processed before Chip in the movement phase, the block starts sliding away in that same tick, and Chip's own real move then usually succeeds. If Chip was holding several directions and another one is chosen, the block still moves.

### 3.1 Block slapping (consequence of the probe quirk)

Players call this **block slapping**. It follows directly from the rules above plus Chip's direction choice (doc 05 §2), and was confirmed on the original ROM:

- **Slap:** Chip stands beside a block and holds two directions, the block's direction being tried first. Example: block to the west, N+W pressed on the same tick (the start-direction table gives W). The probe launches the block west and reports BLOCKED; Chip then tries N and walks north. **Result: the block slides west while Chip walks north.** Both start moving in the same tick.
- **Walking slap:** Chip walks north holding N, and adds W on the tick he is aligned beside a block that lies to his west. W is the newly pressed direction, so it is tried first; same result.
- **180° slap:** block to the east, E+W pressed together (start direction E). **Result: the block slides east while Chip walks west**, away from it.
- **Ordinary push:** with only the block's direction held there is no other direction to try. Chip keeps facing the block, the block (higher slot, processed first) moves away, and Chip's real move then succeeds: he follows the block one tick behind.

A reimplementation that reproduces doc 04 §3 and doc 05 §2 exactly gets all of these for free. Tile World's Lynx ruleset has similar behaviour, but timing details may differ.

## 4. Advancing an object — `advance(i)`

```
advance(i):
  s = state[i]
  if s == 0: return
  if not moving(s): handler(i, STAY); return
  if dying(s): return
  if aligned(i):
      r = test_move(i)
      chip_bump_sound(i, r)                         # §4.1
      if r == BLOCKED:
          if not alive(i): return
          if i == 0 and boots.skates: handler(i, STAY); return
          if ICE(under[i]):                         # ice bounce
              reverse direction (d ^= 2); keep moving flag
              handler(i, ARRIVE); return
          handler(i, STAY); return
      # start the move: lift from current cell, claim the target
      map[cell(i)] = under[i]
      under[i]     = map[target]
      map[target]  = 0x80 | i
  if state[i] != 0:
      step(i)
      if SLIDE(under[i]):                           # tile being entered/occupied
          extra = true
          if i == 0:
              if ICE(under[i]) and boots.skates: extra = false
              if not ICE(under[i]) and boots.suction: extra = false
          if extra: step(i)
  if aligned(i): handler(i, ARRIVE)
```

`step(i)`: if not dying, move `x`/`y` by the type's speed in direction `d` (speed 2 units for all types except **Blob = 1 unit**). The speed and the (dx, dy) pair come from small per-type tables; for the stray types 12–15 (§4.2) those tables are read past their end and the step is not described here.

Consequences:
- Normal move: **4 ticks per tile** (Blob 8). On ice or force floors (and the move *onto* them): **2 ticks per tile** (Blob 4) — "under" is the *destination* tile once a move starts, so the speed-up applies while entering a slide tile and ends on the move that enters a non-slide tile.
- A tile's ARRIVE handler runs at the end of the tick in which the object becomes aligned on it.
- A moving object whose next move is blocked gets STAY handling for that tile (which normally stops it), except for ice bounces.

### 4.1 Bump sound
For Chip only: when a real move test is BLOCKED and Chip is not on a trap, play sfx 08 once; it is not repeated until a move succeeds or Chip releases the controls. (Tracked by a one-shot latch, cleared on success or on "no input".)

### 4.2 Map edges (no bounds checks)
*Verified in emulation with injected test levels and four CCLP1 levels whose monsters leave the map.*

The original never checks the map edge:

- **Target cell** = current cell −32 / +1 / +32 / −1 (plain address arithmetic, no wrap). Leaving the top row therefore addresses the 32 bytes of RAM **just below the map** (cells −32…−1); leaving the bottom row addresses the **object state bytes of slots 0–31** (cells 1024…1055). Leaving column 0 westward lands on column 31 of the *previous* row (or cell −1); leaving column 31 eastward lands on column 0 of the next row (or cell 1024).
- **Coordinates are 8-bit** and wrap on each axis separately (x 0 − 2 = 254). An object's own cell, always computed from its coordinates as `(y/8)*32 + x/8`, is therefore on the *same* row after a horizontal wrap and on row 31 / row 0 after a vertical one — not where its map marker was written. The object effectively becomes detached from its marker; everything then follows from the normal rules applied to the cells actually addressed.
- The bytes read and written are used exactly as map cells: a value `< 0x80` is a tile code, `0x80 | slot` an object reference. Writing a marker into the state table turns that slot into a stray object.
- **The RAM below the map** holds the high bytes of the link table entries of row 31 (doc 02 §5): for a row-31 brown/red button, `0x0C | (target >> 8)`; for a row-31 teleport, the target's y coordinate (`row × 8`). Other bytes keep whatever an earlier level stored there (zero from power-on), so they normally read as floor.
- **Tile codes past `0x33`** (they can only come from those bytes) read the property tables beyond their end (doc 03 §1). The entry mask of code `0x34 + k` is the leave/flag byte of code `k`; everything else past the tables — entry masks of codes `≥ 0x68`, flags of codes `≥ 0x34`, the class masks of stray types, what a handler past the table does — was **measured** and is listed in §4.4. Most codes crash the original when an object arrives on them.

Levels designed for the cartridge keep a wall border, so none of this is reachable there; imported levels with open edges can reach it. A reimplementation that only needs cartridge levels may treat off-map moves as blocked.

### 4.3 Ways the original fails (imported levels only)
*Found by injecting 246 imported levels (CCLP1, CCLP5, three "geo" sets) and replaying their solutions; each is reproduced by the remake on the same tick.*

| Condition | Result on the original |
|---|---|
| A brown or red button with no trap / clone machine anywhere on the map (doc 02 §5) | hangs while the level starts (tick 0) |
| An object arrives on or stands on a tile code `≥ 0x34` (§4.2) | crash for most codes; ten codes do not (§4.4) |
| The decision phase meets a slot of type 12, 14 or 15 (§2) | crash |
| An effect reaches a frame `≥ 0x12` (§8) | continues with the next states measured in §4.4 |
| An effect is removed but its map reference is at none of the three probed cells (§8) | continues with corrupted state (not described) |
| **Display hang:** a cell inside the 11 × 11 drawn window (doc 06 §4.1) holds an object reference whose chain *object → its under-tile → …* loops back on itself | hangs while drawing (the next frame never completes) |

The display hang needs stray writes off the map edge: a marker written into the object state table (cells 1024…) can make a slot's `under` point at an object whose `under` points back. The drawn window is the 11 × 11 cells whose top-left cell is `(cx >> 2, cy >> 2)` with `cx = clamp(x_chip/2 − 16, 0, 93)` and `cy` likewise; cells outside the map are drawn as cell 0.

**Death reason default.** The death-reason byte is set to *time-out* when an attempt starts and is overwritten only by a recorded cause (killed, drowned, burned …). A Chip whose slot is cleared by a stray write therefore ends the attempt as a time-out.

### 4.4 Behaviour past the tables (measured)
*Everything in this section was obtained by black-box experiments: small test levels (and, where needed, one byte of game state set after the level started) were run on the original and the outcome observed — did the object move, how far, what did the map and slot tables hold afterwards, did the program crash. No program bytes were read. About 3000 of these scenarios were then replayed in lock-step against an engine built from this section; all match except the display effects described at the end.*

**Who may enter what.** The rule of §3 still holds — a tile is passable when `entry_mask(v) & class_mask(mover)` is zero; *special* tiles block everyone but go through `special_bump` for Chip — with these additions:

- **Class masks of the stray types**, per direction N/E/S/W: type 0 `00 00 00 00`; types 12 and 13 `00 00 00 00`; type 14 `00 00 05 00`; type 15 `20 DB 3D BD`. (Type 0 appears as a state byte `80`–`83`, "moving nothing", e.g. from effect frame `3B` below.) These are masks consistent with every observation; bits that no tile uses cannot be told apart.
- **Leave check:** the leave mask of the tile the mover stands on is tested against the low four bits of its class mask (`leave & class & 0F`). For every real type that is just its own direction bit (§3 as written); type 0 can leave anything, and the stray types use their masks above.
- **Codes `34`–`67`:** entry mask = leave/flag byte of code `c − 34` (§4.2), so it changes when that tile's leave mask changes (suction boots, trap and cloner release) — except codes `34 3A 3B 3C 45 47 4C`, which are *special*: nobody enters them.
- **Codes `68`–`7F`:** the table below gives an entry mask consistent with all observations.
- **Byte values `80`–`FF` used as a tile.** An object reference can end up as an object's under-tile, e.g. when Chip walks off the bottom edge onto a state byte that reads as a Chip-type object (passable, §3). Such a value has its own entry/leave masks and slide/ice flags (second table). Its ARRIVE/STAY handler does nothing: the mover keeps its moving flag.

**Codes `34`–`7F`:**

| Code | Entry | Slide | Ice | On arrival | Leave |
|---|---|---|---|---|---|
| `34` | none (special) |  |  | crash |  |
| `35` | = leave/flag byte of `01` |  |  | crash |  |
| `36` | = leave/flag byte of `02` |  |  | crash |  |
| `37` | = leave/flag byte of `03` | yes |  | crash |  |
| `38` | = leave/flag byte of `04` | yes |  | crash |  |
| `39` | = leave/flag byte of `05` | yes |  | crash |  |
| `3A` | none (special) |  |  | crash |  |
| `3B` | none (special) |  |  | crash |  |
| `3C` | none (special) |  |  | crash |  |
| `3D` | = leave/flag byte of `09` |  |  | crash |  |
| `3E` | = leave/flag byte of `0A` | yes |  | crash |  |
| `3F` | = leave/flag byte of `0B` | yes |  | crash |  |
| `40` | = leave/flag byte of `0C` | yes |  | crash |  |
| `41` | = leave/flag byte of `0D` |  |  | crash |  |
| `42` | = leave/flag byte of `0E` | yes | yes | crash |  |
| `43` | = leave/flag byte of `0F` | yes |  | move on at once; STAY crashes | `3` |
| `44` | = leave/flag byte of `10` |  |  | crash |  |
| `45` | none (special) |  |  | crash |  |
| `46` | = leave/flag byte of `12` |  |  | crash |  |
| `47` | none (special) |  |  | crash |  |
| `48` | = leave/flag byte of `14` | yes | yes | crash |  |
| `49` | = leave/flag byte of `15` |  |  | crash |  |
| `4A` | = leave/flag byte of `16` | yes | yes | move on at once; STAY crashes | `9` |
| `4B` | = leave/flag byte of `17` |  |  | crash |  |
| `4C` | none (special) |  |  | crash |  |
| `4D` | = leave/flag byte of `19` |  |  | crash |  |
| `4E` | = leave/flag byte of `1A` | yes | yes | crash |  |
| `4F` | = leave/flag byte of `1B` |  |  | keep moving | `0` |
| `50` | = leave/flag byte of `1C` |  |  | crash |  |
| `51` | = leave/flag byte of `1D` |  |  | crash |  |
| `52` | = leave/flag byte of `1E` |  |  | stop | `0` |
| `53` | = leave/flag byte of `1F` |  |  | crash |  |
| `54` | = leave/flag byte of `20` |  |  | crash |  |
| `55` | = leave/flag byte of `21` |  |  | crash |  |
| `56` | = leave/flag byte of `22` |  |  | crash |  |
| `57` | = leave/flag byte of `23` | yes | yes | crash |  |
| `58` | = leave/flag byte of `24` | yes | yes | crash |  |
| `59` | = leave/flag byte of `25` | yes | yes | crash |  |
| `5A` | = leave/flag byte of `26` | yes | yes | crash |  |
| `5B` | = leave/flag byte of `27` | yes | yes | crash |  |
| `5C` | = leave/flag byte of `28` | yes | yes | stop | `2` |
| `5D` | = leave/flag byte of `29` | yes | yes | crash |  |
| `5E` | = leave/flag byte of `2A` | yes | yes | crash |  |
| `5F` | = leave/flag byte of `2B` | yes |  | crash |  |
| `60` | = leave/flag byte of `2C` | yes |  | crash |  |
| `61` | = leave/flag byte of `2D` | yes |  | crash |  |
| `62` | = leave/flag byte of `2E` | yes |  | crash |  |
| `63` | = leave/flag byte of `2F` | yes |  | crash |  |
| `64` | = leave/flag byte of `30` | yes | yes | crash |  |
| `65` | = leave/flag byte of `31` | yes | yes | crash |  |
| `66` | = leave/flag byte of `32` | yes | yes | crash |  |
| `67` | = leave/flag byte of `33` | yes | yes | crash |  |
| `68` | `3D` | yes | yes | crash |  |
| `69` | `00` | yes | yes | crash |  |
| `6A` | `11` | yes | yes | crash |  |
| `6B` | `4A` |  |  | keep moving | `1` |
| `6C` | `4A` |  |  | crash |  |
| `6D` | `4A` |  |  | crash |  |
| `6E` | `28` |  |  | crash |  |
| `6F` | `3D` | yes | yes | crash |  |
| `70` | `80` | yes | yes | crash |  |
| `71` | `10` | yes | yes | move on at once; STAY does nothing | `4` |
| `72` | `4A` | yes | yes | crash |  |
| `73` | `4A` | yes | yes | crash |  |
| `74` | `4A` | yes | yes | crash |  |
| `75` | `18` | yes | yes | keep moving | `4` |
| `76` | `39` | yes | yes | crash |  |
| `77` | `13` | yes | yes | crash |  |
| `78` | `2F` | yes |  | crash |  |
| `79` | `05` | yes | yes | crash |  |
| `7A` | `0B` | yes | yes | keep moving | `0` |
| `7B` | `39` | yes | yes | crash |  |
| `7C` | `37` | yes | yes | keep moving | `0` |
| `7D` | `2F` | yes |  | crash |  |
| `7E` | `69` | yes | yes | crash |  |
| `7F` | `00` |  |  | crash |  |

*Crash*: the arrival (or any handler call while standing on it) jumps into unrelated code and the program crashes or hangs. On a sliding code the arrival — and the crash — comes 2 ticks after the move starts, otherwise 4. *Stop*: like floor. *Keep moving*: like a trap without a button; the object keeps its moving flag and goes on next tick if the leave mask lets it (if not, an *ice* code bounces it, otherwise it waits). *Move on at once*: on arrival the object is advanced again in the same tick (§4), from the code itself. If that move is blocked by the code's leave mask, the usual rules apply: on an *ice* code the object bounces (reverses) and arrives again — which moves it straight back off the code — otherwise, and for Chip on skates, its STAY handling runs, which crashes on `43` and `4A` and does nothing on `71` (the object waits there, still moving). So `4A` turns arrivals from N and W back to S and E, `71` turns an arrival moving S back north, and `43` crashes on arrivals moving N or E. Stray movers (type 0, 12–15) are never stopped by a leave mask (above) and simply move on. A re-move blocked in both directions bounces without end (the "acting wall, ice, acting wall" case: Chip entering `71` northward with an acting wall ahead, since its leave mask blocks the way back south). The original does not settle into one bounce per tick: the endless recursion runs into the stack, and what follows depends on the stack's contents — sampled once per tick, Chip's direction flips N/S irregularly, other objects get extra moves (the pattern changes with the number of objects in the level), and sometimes the program crashes. The remake stops the chain (Chip waits on the code) and shows the desync notice; in tests the first 3 ticks after the arrival match. For any other object the original usually crashes in the same situation, but not always (random survey, doc 09 §22); the remake crashes after 32 nested re-moves, as before, and shows the desync notice.

*Code `71` and the sound driver (measured).* What `71` does depends on one byte of the sound driver's working memory (`795B`), which the music changes many times a tick. The driver's interrupt rewrites it within a tick, so it was measured with an emulator hook that blocks all writes to it (`tools/measure/lock71.py`; poking it before each tick is not enough). (1) **A Chip-type object arriving** on `71` — Chip with or without boots, or a fake Chip in another slot: with the byte at `3C` it is moved on at once (the rule above); at `0` it is not — it stays on `71` for that tick, still moving, and goes on next tick (42 of 72 real-Chip set-ups and every fake-Chip arrival differ between the two values; Chip on skates walking onto it was moved on with neither value in these tests). Other movers cannot enter `71`. (2) **An object standing on `71`** (its STAY, e.g. a block resting there): by the same byte the original holds Chip's own movement back. (3) **An object whose move is blocked while on `71`** (a tank facing a wall or another `71`, a blob that tries to step onto a neighbouring `71`): this runs the same code, and with the byte non-zero another object gets one extra step that tick. The remake does not emulate the sound driver: in all three cases it keeps a plain rule (the real Chip moved on at once, a fake Chip waiting) and shows the desync notice (unmapped memory). An earlier version of this paragraph limited case 1 to Chip on skates; that came from poking the byte only between ticks.

**Byte values `80`–`FF` as tiles** — `entry/leave` (hex), `s` = slide, `i` = ice:

| | +0 | +1 | +2 | +3 | +4 | +5 | +6 | +7 |
|---|---|---|---|---|---|---|---|---|
| `80` | 05/0 | 0C/0 | 40/0 | 00/0 | 00/0 | 00/0 | 00/0 | 01/0 |
| `88` | 02/0 | 04/5 | 08/0 | 11/0 | 12/B s | 14/D i | 18/D i | 11/0 |
| `90` | 12/0 | 14/9 | 18/0 s | 11/0 si | 12/3 | 14/9 i | 18/1 | 11/0 si |
| `98` | 12/9 i | 14/F si | 18/8 i | 11/9 i | 12/6 si | 14/D i | 18/5 | 11/7 |
| `A0` | 12/C i | 14/0 | 18/2 | 11/9 i | 12/7 i | 14/D i | 18/9 i | 11/F |
| `A8` | 12/0 s | 14/4 i | 18/D i | 11/0 | 12/0 | 14/9 i | 18/3 | 11/8 i |
| `B0` | 12/5 i | 14/B | 18/8 | 00/9 si | 00/7 | 00/F i | 00/5 | 00/D |
| `B8` | 00/5 i | 00/C | 00/9 si | 00/B | 00/F i | 05/5 | 00/E | 20/2 i |
| `C0` | 1B/D | 1D/0 | 1D/C | 00/8 i | 10/9 i | 09/7 i | 40/D i | 10/0 |
| `C8` | 03/9 si | 29/9 i | 01/3 si | 40/D i | 29/5 i | 0F/7 | 28/0 si | 19/9 i |
| `D0` | 16/F si | 1D/8 i | 05/9 i | 17/0 | 1C/2 | 00/8 i | 12/9 i | 19/3 si |
| `D8` | 27/D i | 1D/5 i | 29/7 | 0F/0 s | 10/1 si | 24/2 i | 1D/D | 00/0 si |
| `E0` | 10/0 | 29/0 si | 03/4 i | 28/9 i | 25/F si | 0B/8 i | 18/9 i | 19/0 |
| `E8` | 07/0 | 0F/9 | 05/0 s | 0D/0 si | 25/D | 0C/9 i | 19/0 | 0B/2 |
| `F0` | 0F/2 | 05/D | 0E/9 i | 12/0 | 0D/9 | 10/0 | 0C/0 | 28/C s |
| `F8` | 19/2 i | 27/E i | 1D/0 s | 10/0 | 19/0 si | 19/3 | 13/9 i | 1D/1 |

**Stray types 12–15 — step per tick** (dx, dy in 1/8-tile units, 8-bit wrap; doubled on sliding tiles, as for every type):

| Type | N | E | S | W |
|---|---|---|---|---|
| 12 | −128, −99 | 19, −128 | 32, 19 | 60, 32 |
| 13 | 21, 57 | 30, 21 | −16, 30 | 29, −16 |
| 14 | 32, 18 | 60, 32 | 29, 60 | −115, 29 |
| 15 | −115, 3 | 73, −115 | 29, 73 | −83, 29 |

Type 0 moves like the ordinary types (2 units). In the decision phase types 12, 14 and 15 crash and type 13 advances the RNG (§2).

**Effect frames past the table.** On the next odd tick the state byte is replaced by the value listed; `00` means removed as in §8, and any other value simply becomes the slot's new state, which may be a live (even moving) object: `12`→`6A` `13`→`3C` `14`→`6D` `15`→`1D` `16`→`F2` `17`→`3C` `18`→`F6` `19`→`3C` `1A`→`FE` `1B`→`3C` `1C`→`FA` `1D`→`3C` `1E`→`02` `1F`→`3D` `20`→`06` `21`→`3D` `22`→`E6` `23`→`3C` `24`→`07` `25`→`3D` `26`→`6B` `27`→`3C` `28`→`89` `29`→`3C` `2A`→`60` `2B`→`20` `2C`→`DC` `2D`→`3B` `2E`→`45` `2F`→`2F` `30`→`29` `31`→`03` `32`→`5D` `33`→`00` `34`→`10` `35`→`29` `36`→`03` `37`→`5D` `38`→`00` `39`→`10` `3A`→`09` `3B`→`80` `3C`→`9D` `3D`→`00` `3E`→`10` `3F`→`60`.

**Link table and memory.** The button/teleport link table is two 1024-byte halves (low bytes, high bytes, indexed by cell). The original **never clears** it: at level start only the entries of source cells are written, so all other entries keep values from earlier levels. A button's entry is the target's address `0C00 + cell` (low byte in the first half, high byte `0C`–`0F` in the second). A teleport's entry is the target's x coordinate (first half) and y coordinate (second half). The high half of row 31 is the RAM above the map (cells −32…−1), so an off-map write can change it, and the original uses the changed value when the button is pressed or the teleport is used:

- A **brown/red button** acts on whatever byte that address holds. A byte `≥ 80` is taken as an object to release or clone, and a clone's reference is then *written* to that address — in the zero page that changes, for example, the chips-left counter. Any other byte means "no object".
- A **teleport** jumps to the coordinates read. If no free teleport is there, the search goes on from that cell's (possibly stale) entry, writing the teleport tile back into every cell it passes (the quirk of §6). If it never finds one, the original hangs.

Game-state addresses reachable this way (verified by observation):

| Address | Holds |
|---|---|
| `20`–`23` | boots (skates, suction, fire, flippers) |
| `26`/`27` | chips left |
| `28` | level finished |
| `2A`–`2D` | keys (red, blue, yellow, green) |
| `2F` | tick |
| `0400`–`0BFF` | link table |
| `0C00`–`0FFF` | map |
| `1000` / `1080` / `1100` / `1200` | slot tables: state / x / y / under (128 bytes each) |
| `1180`/`1181` | time left |

Other addresses are not described. Every observed read of them behaved as "no object", which is what a reimplementation should assume.

**Display.** *Mechanism (measured).* To draw a tile or an object the game looks up a sprite control block for it and first **writes the item's screen position into that block** (x low byte at the block's position field, y two bytes later). For tile codes past `33`, and for objects in stray states, the lookup runs past its table, so the position is written to an unrelated address — a fixed address per code — and the sprite engine then draws whatever is there. Observed write addresses include object state/x tables (codes `3F`, `47` → state of slots 7 and 9; `45` → x of slots 81 and 83), the link table (`39 3B 3D 44 5C 62 64 7B 7D`), the zero page and stack (`35 3C 41 4A 49 63`), other sprites' blocks (harmless) and program code (`37 38 61 6E` and others). The value written is the screen position (12 px per cell; with the camera at rest on Chip in mid-map, 12 × column − 105 and 12 × row − 105 for the cell's column and row). A write into program code makes the original crash later, when that code runs; so the visible effect depends on the code, the screen position (the value written) and what runs afterwards.

*Chip drawn in a junk state.* When an off-map write puts an object reference into Chip's state byte, the original crashes — with at least one other object on screen — this many ticks after the write: `F8` the same tick; `D2`–`E2` and `F4` one tick; `E8` one tick if the write happens on an even tick, else two; `EA EC F2 F7 FF` two ticks (even) or three (odd). Other values are harmless when drawn. (With nothing else on screen the delays are one tick longer.)

*Odd tile codes, grouped (measured).* The write is four bytes: screen x as a 16-bit value at the code's address A, screen y as a 16-bit value at A+2 (the high bytes are 0 while the cell is on screen). It is repeated every frame the cell is in view, so the values follow the camera. Grouping the 76 codes by where A lands, testing one code per group and then every member (Chip idle, Chip walking, a bouncing ball, and a course over a chip, key, skates, both button kinds, a hint, ending on the exit or in water) gave:

| Group | Codes | Effect in play |
|---|---|---|
| Other sprites' blocks | `4C`–`57` `6B` `71` `74` `7A` | none |
| Graphics / screen memory | `36 3E 46 59 5A 5B 5D 5E 65 66 68 69 6D 72 75 76 7E` | none |
| No write found in RAM | `48 58` | none |
| Program code that does not run during play | `34 37 3A 40 42 43 4B 5F 67 6A 6C 6F 70 73 77 78 79 7C` | none |
| Scratch memory | `35 3C 41 4A` (zero page), `49 63` (page 2) | none |
| Program code that runs every tick | `61`, `6E` | crash on the next tick (`6E`: 6 ticks in some columns) |
| Program code of Chip's move | `38` | crash once Chip moves, for most written values |
| Slot state table | `3F`, `47` | states of slots 7–10 = x lo, x hi, y lo, y hi: those slots become stray objects (doc 04 §4.4 tables apply; some values crash once Chip moves) |
| Slot x table | `45` | x of slots 81–84 |
| Link table | `39 3B 3D 44 5C 62 64 7B 7D` | the links of four consecutive cells (low or high half) are overwritten: a button or teleport there is re-aimed |
| Tile entry masks | `60` (codes `2B`–`2E`), `7F` (keys `1E`–`21`) | those tiles' entry masks become x lo, 0, y lo, 0. Verified: with `7F` in view, Chip walking east is stopped by a red or yellow key, and the blue and green keys become open to all movers |

So 59 of the 76 codes have no effect on play and 17 do (`38 3F 45 47 60 61 6E 7F` and the nine link codes); apart from the three live-code crashes every effect is a plain data write that a memory-model reimplementation can repeat. An engine that pokes junk states into slots 7 and 9 matched the original in all 512 cases tried (every value, Chip moving).

*Reproducing the writes (measured).* The play field is drawn once after every tick (not before the first). The drawn cells are the 11 × 11 cells from column `cx/4 − 1` and row `cy/4 − 1` (camera of doc 06 §4.1, so centred on the camera), addressed linearly as `row·32 + column`: column −1 of a row is column 31 of the row above, column 32 is column 0 of the row below, and addresses outside 0–1023 draw the tile of cell 0. A cell holding an object draws the end of its under-tile chain. The written values are `x = 12·column − 3·cx + 27` and `y = 12·row − 3·cy + 27` (always 6–135, so the high bytes are 0). Cells are drawn bottom-right first, so when two cells write the same address the first cell in reading order wins. The three code-damage cases:

- `61`: every later tick crashes (the next tick after the first draw).
- `6E`: the last x value written decides: for some values the next tick crashes, for the others the next tick whose index since level start is a multiple of 6 (the 6-tick tile animation cycle). Measured table of all 256 values in the remake (`draw_tables.inc`). Before that crash, the damaged animation code can write further screen positions into the slot tables — not modelled.
- `38`: the next move test or arrival of **any** object crashes (Chip pressing a direction, Chip or a monster reaching a cell, a monster choosing a direction). Exception: x = 96 (`0x60`) does not crash. Instead the game's cell lookup stops computing: every lookup of an object's cell (move tests, leaving a cell, arriving, teleports, buttons) returns the last cell computed. That is slot 0's cell at level start; after every drawn frame the cell above the window's top-right corner, `32·(r0 − 1) + c0 + 10` (linear, so it can lie off the map); and after a brown or red button acts, the link address it just looked up (read for the stale cell, so often `0000`: moves then work on zero-page RAM). Chip's direction choice keeps the moving flag even when its test fails, so the move is tested again in the movement phase, after other objects' buttons may have changed the stale cell. Further measured rules in this state: an object arriving on a teleport while moving **east or west** makes the original hang; moving north or south, its under-tile is written to the stale cell and it lands at (0, 0), still moving (with a non-empty link on the stale cell, or the cell beyond it blocked, the search instead wanders through untracked memory). When the camera leaves its clamp, the written x changes (for example to 99) and the damaged code then crashes at the next cell lookup of any kind — move tests and arrivals, but also a button acting and an effect being removed at the end of a death. Objects then move on the map "from" that cell: the old cell's reference is not cleared, a reference is written next to the stale cell, the under-tile is read there (so slide tiles stop giving their double step), and collisions are found there (Chip can be killed by a monster far away). In practice x = 96 needs the camera at its right-edge clamp with `38` in column 29, where it stays 96 every frame.

The original never restores program bytes, so this damage would last until power-off. The remake resets it with each level, by choice (decisions log).

*Accuracy.* With these rules the remake matched the original in **2858 of 2869** random lock-step scenarios using one of the 17 effective codes (random tiles, monsters and input, 48 ticks each; 977 of them crash on the original). Without the drawing rules it matched 1515. The 11 misses: 9 are `6E` before its crash (the extra writes above; they now raise the desync notice whenever an animated tile — exit, water, fire, teleport — is in view while 6E's damage waits, which covers all of them) and 2 are other stray-object effects. In 1695 extra scenarios forcing `38` to x = 96 (three seeds) the remake matches the original in 1681 (73 without the stale-lookup rules). Each of the 14 others involves memory the remake does not track — zero-page scratch bytes read by a stale move, or a teleport search that wanders — and in every one the remake raises its out-of-sync flag (the game shows "Desync with Lynx CC1") no later than the first difference. The flag also rose in some runs that still matched, and never in a run without the x = 96 state. The existing 3038-scenario suite now matches completely (the 10 display cases are fixed), and all level-pack oracles are unchanged.

*Re-aimed button links.* When an odd tile's drawing write lands on the link table, a button there points at an address built from a screen position — typically sprite or program memory. The original then reads whatever byte is there; a stray `81` in sprite memory counts as object 1 and gets an extra move from the "button" (observed with `7B`, which points a button at `48DA`). The remake holds no such memory and reads "no object", so it shows the desync notice when a button acts through a link that drawing has overwritten. (Stale links in real levels also point at unmodelled memory, but always behaved as "no object", so those are not flagged.)

*Object drawing into code.* As with odd tiles, a stray object's drawing write can land in program code that runs later: in one test, objects that code `47` turned into state `7B` wrote to `A7F9` every frame, and the original crashed (invalid instruction) the next time Chip moved south. Not modelled yet; the per-state table of such crashes is open.

*Stray objects drawn (measured, `tools/measure/objaddr.py`).* Objects are drawn after the tiles, found through the object references in the drawn cells (reading order), at `x = 3·(x/2 − cx) + 27`, `y = 3·(y/2 − cy) + 27` (the same as a tile in that cell), and an object in a stray state writes this position (16-bit x, 16-bit y) to a fixed address per state; bit 7 of the state does not matter. Of all 255 states, two land on game data the remake models: `68`/`E8` → slot states 69–72, and `75`/`F5` → the **row table of the cell lookup** (entries for rows 16–19). Others land in sprite blocks, program code (Chip's crash table above covers those for slot 0), the stack and zero-page scratch.

*Row table.* The game finds an object's cell as `256·(row / 8) + T[row] + column`, where `T[row]` (32 entries, normally `row · 32` mod 256) is a table in RAM. Every object in every direction goes through it, and the target cell is that result plus the step. When a stray `F5` overwrites entries, objects in those rows act on a shifted cell: they leave their old reference behind, test and enter the shifted neighbour, and can walk through walls. This is what happens on Joshie level 511, which now matches. The drawing of objects also depends on the table (measured, `tools/measure/objscan.py`: every cell of a block filled with parked tanks, sprite-memory writes logged, all 256 values of an entry, 64 256 / 64 256 cells match). The object pass looks up **only the window's last row** through the table, `base = 256·(L / 8) + T[L] + c0` with `L = r0 + 10`, and reaches the rows above by stepping back 32 cells each: it visits `base − 32·(10 − m) + k` for `m, k = 0…10`, in reading order. Every visited map byte with bit 7 set is taken as an object reference; addresses outside the map are skipped, at both ends (measured: an object-table byte past the end and a link-table byte before the start, each pointing at a row-table writer, are never drawn, even on a valid window row, and the scan does not wrap). So a shifted `T[L]` moves the whole scanned window by the shift in cells (whole rows included, e.g. `00` in place of `60` scans three rows higher). The table runs on past row 31 (four more entries with the normal values, used when the camera is at the bottom). A stray object's position write happens whether or not the object is on screen; ordinary objects off the left or top edge are not drawn. Chip is drawn separately and always. With this rule the random lock-step tests (four seeds, 3950 runs with states 68/75/E8/F5 in view) match in all but 1, a state-`7B` likely-crash case announced by its notice one tick ahead; the per-tick draw decision for the row-table writer matches 41 513 / 41 513 ticks (the old low-5-bit rule missed 849, all the mid-scroll cases among them).

*Two kinds of desync notice.* "A rare glitch reached unmapped memory" — the outcome depends on RAM or program state the remake does not hold (zero-page scratch, sprite memory behind a re-aimed link, the stack, 6E's animation writes, stale teleport searches). "A rare glitch hit behaviour not yet mapped" — the mechanism is known but its exact rule is not: an object in state `7B` (drawing writes into code that crashes when Chip next moves south). Other states whose drawing writes into code appear in real levels (CCLP5 20, Jacques 242) without any effect, so they are not flagged. Across all real replays the notice no longer appears (Joshie 511, the row-table level, matches without it).

Program damage of any kind is reset with each level in the remake (by choice).

Not yet described: the crash delays of junk states in slots other than 0.

## 5. Tile handlers
See doc 03 §3. Handlers receive the event (ARRIVE/STAY) and may change the object's direction/moving flag, the tile under it, inventory, or global flags. The default handler stops the object (clears moving).

## 6. Teleport

Runs as the ARRIVE handler of a teleport for any mover `i` (Chip gets sfx 03 first):

```
origin = (x, y) of i
loop:
    map[cell(i)] = under[i]                       # vacate current teleport
    move i to the teleport linked from its current cell (doc 02 §5)
    if map[that cell] != TELEPORT:                # occupied by an object → skip it
        continue loop                            # (quirk: see note)
    under[i] = TELEPORT; map[cell] = 0x80 | i
    probe = 0x80; r = test_move(i); probe = 0
    if r == PASSABLE: return                     # keeps moving flag: exits next move
    if not alive(i): return
    if (x, y) == origin: stop i; return           # every teleport blocked: stays put
```

- The mover keeps its direction; it exits the destination teleport on its next movement.
- While Chip stands on a teleport his input is ignored (doc 05 §2), so he always leaves in his arrival direction.
- *Quirk (original):* when a destination teleport is occupied, the loop first writes the teleport tile back into that occupied cell, detaching the occupant from the map. Reproduce only if exact fidelity is wanted; otherwise just skip occupied teleports.

## 7. Traps and clone machines

**Trap release** (brown-button handler, on ARRIVE and STAY): if the linked trap cell holds object `k`, temporarily set the trap's leave mask to 0, run `advance(k)` immediately, then restore the mask. An object waiting in a trap keeps its moving flag (doc 03 §3.16, doc 02 §4 step 6), so it walks out in its facing direction. Chip may change his facing while trapped (his input handler still runs), and leaves in the last chosen direction.

**Cloning** (red-button handler, ARRIVE only): let `L` be the linked cloner cell.
```
if map[L] holds object k:
    snapshot = (state, x, y, under) of k
    cloner leave mask := 0; advance(k); cloner leave mask := all
    stop the presser
    if map[L] still holds an object: return       # template could not leave
    s = lowest free slot in 1..127; if none: return
    slot s := snapshot; map[L] := 0x80 | s        # new template in the cloner
    sfx 05
else stop the presser
```
Templates sit in cloners with their moving flag set, so they never run AI; the released copy keeps the template's type and direction. Blocks can be cloned like any object.

## 8. Effects (dying objects)

An object with the dying flag is a visual effect occupying its cell. Its low 6 bits are a frame number:

| Effect | Frames | Used for |
|---|---|---|
| Explosion / burn | `0x40 → 0x45` | Bombs, Chip burning |
| Chip death | `0x46 → 0x4B` | Chip killed by a monster/block, time-out |
| Splash | `0x4C → 0x51` | Drowning (Chip, monsters, blocks) |

Each frame advances on **odd ticks** (≈ 2 ticks per frame, 6 frames). After the last frame the object is **removed**: the new state (0) is stored first, then its map reference is looked for at its cell, then at the cell east (+1), then south (+32) (an object killed mid-move is referenced from its destination); the first match is replaced by `under`, and the slot is cleared. If the object's own `under` is itself an object reference, nothing is removed. If none of the three cells holds the reference (only possible after off-map writes) the original goes on with inconsistent state (§4.3).

Effects block other movers (they are objects), except that a monster/block test-moving into an effect erases it (§3).

The next frame comes from a 64-entry table indexed by the frame number. Frames `00–11` are the three effects above; a dying state with a frame `≥ 0x12` exists only as a stray byte written off the map edge (§4.2) — its next states were measured (§4.4).

## 9. Creature AI

Runs in the decision phase for an **idle, aligned, alive** object. Each AI produces a direction and sets the moving flag. Candidate lists are tried in order with `test_move` (`probe = 1`); the first PASSABLE candidate is kept; if the object dies during a test, stop; **if all candidates fail, the last candidate remains selected** (the move will fail and the tile's STAY handler will stop it; it retries next tick).

Candidates are relative to the current direction `d`:

| Type | Candidates |
|---|---|
| Bug | left (d+3), forward, right (d+1), back (d+2) |
| Paramecium | right, forward, left, back |
| Fireball | forward, right, left, back |
| Glider | forward, left, right, back |
| Ball | forward, back |
| Tank | forward only; **if `tank_reverse == 2`: back only** |
| Walker | forward; if blocked: `d + (rng.next() & 3)` (one random try; may equal forward) |
| Blob | no test: `d = (rng.next() XOR tick) & 3`, moving flag set |
| Teeth | see below |
| Block | none (moves only when pushed / slid / released) |

Note the cumulative form: e.g. Bug's "forward" after "left" is d+3+1.

**Teeth** (only on ticks where `tick & 4 ≠ 0`; otherwise it does nothing and stays idle):
```
dx = x_teeth − x_chip ; dy = y_teeth − y_chip       (in 1/8 units)
horiz = W if dx ≥ 0 else E ; vert = N if dy ≥ 0 else S
if |dx| > |dy|: primary = horiz, secondary = vert, sec_dist = |dy|
else:           primary = vert,  secondary = horiz, sec_dist = |dx|
choose primary (moving flag set); if test_move PASSABLE: done
if teeth died: done
if sec_dist != 0: choose secondary (no test)
```
Combined with 4-tick moves, the tick gate makes Teeth move one tile every 8 ticks (half speed).

**Tank reversal:** the blue button toggles bit 0 of `tank_reverse`. At the end of every tick (running or not) `tank_reverse` is updated by the table `0→0, 1→2, 2→0, 3→1`. So a press makes `tank_reverse == 2` during exactly one subsequent decision phase, in which **idle** tanks pick "back". Tanks that are mid-move at that moment do not reverse.

**Monsters probing Chip:** because `test_move` kills Chip when a monster's candidate cell holds him, a monster kills Chip as soon as its candidate scan reaches Chip's cell — this matches "the monster moves into Chip".

## 10. Effects on the RNG

`rng.next()` is consumed only by Walker (when its forward is blocked) and Blob decisions, in slot order 127→1 within each tick. With the per-attempt reset to (0,0) and the global `tick`, monster behaviour is deterministic for a given input sequence and starting `tick` value.
