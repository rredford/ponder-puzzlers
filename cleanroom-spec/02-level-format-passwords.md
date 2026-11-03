# 02 — Level Data Format, Links & Passwords

## 1. Level numbering

- 150 level slots; slot *N* (1-based) is stored in directory file `21 + N`.
- Slots **1–144**: the main sequence, played in order.
- Slot **145**: an *end-of-game marker* (file content is the single byte `0xFF`). Finishing level 144 leads here → ending sequence (doc 06 §8).
- Slots **146–149**: bonus levels, reachable only by entering their password.
- Slot **150**: end-of-game marker (single byte `0xFF`); finishing level 149 leads here.
- Internally the game uses a 0-based level index `L = N − 1`.

## 2. Level file layout (decoded size ≈ 1 415–1 530 bytes)

| Offset | Size | Content |
|---|---|---|
| `0x000` | 1024 | **Map**: 32 rows × 32 columns, row-major (`row*32 + col`). Each byte is a tile code `0x00–0x33` (doc 03). Under every creature the map holds the tile the creature stands on. |
| `0x400` | 128 | **Object state byte** for slots 0–127 (0 = empty slot) — §3 |
| `0x480` | 128 | **X position** of each slot, in 1/8-tile units (`col × 8`; always a multiple of 8 in level files) |
| `0x500` | 128 | **Y position** of each slot, in 1/8-tile units (`row × 8`) |
| `0x580` | 2 | **Time limit** in seconds, unsigned 16-bit LE. `0` = untimed level. Observed values 0–999. |
| `0x582` | var | **Title**: text in the game charset (doc 06 §6), terminated by `0x00`. |
| after title | var | **Hint text** (optional): zero or more lines, each terminated by `0x00`; the list ends at an empty line (an extra `0x00`) or at end of file. Most levels have no hint. |

**Text limits.** Real levels use titles and hint lines of at most 19 characters and at most 7 hint lines; title plus hints must fit in the 126 bytes before the object under-tile table that follows the level buffer. A hint line longer than 19 characters crashes the original when the hint is shown (found while injecting converted levels).

Total length is not stored; it is the decoded length of the file.

### 2.1 Required counts derived from the map

- **Chips required** = number of cells containing tile `0x23` (counted when the level is loaded). Tile `0x31` looks identical but is *not* counted (doc 03).
- The *socket* tile becomes passable for Chip when chips-required reaches 0.

### 2.2 Invariants observed in all 148 real levels

- Slot 0 is always Chip (type 1).
- No slot has the "dying" flag (bit 6) set.
- The "moving" flag (bit 7) is set **only** for creatures standing on a **clone machine** (`0x2F`) — these are cloner templates.
- Creatures may start on many tile types (floor, traps, water, fire, ice, chips, buttons, …).

## 3. Object state byte

```
bit 7   M  moving / committed to a move in the current direction
bit 6   D  dying / effect animation (object is a visual effect, not a live creature)
bits 5–2 T  type
bits 1–0 d  direction (0=N, 1=E, 2=S, 3=W)
```

| T | Type | Notes |
|---|---|---|
| 0 | (none) | Unused |
| 1 | **Chip** | Slot 0 only |
| 2 | Bug | Left-wall follower |
| 3 | Paramecium | Right-wall follower |
| 4 | Fireball | |
| 5 | Glider | Can swim |
| 6 | Ball | Bounces |
| 7 | **Block** | Pushable block (an object, not a tile) |
| 8 | Tank | |
| 9 | Walker | |
| 10 | Blob | Slow, random |
| 11 | Teeth | Chases Chip, slow |

When D is set, bits 5–0 instead hold an animation frame number (doc 04 §8).

## 4. Level initialisation (performed when a level attempt starts)

In this order:

1. Load the level file into a fresh level state (map, slot tables, time, text).
2. **Count chips** (`0x23` cells) → chips-left. There is no chips-required field: a level always needs exactly the counted chips it holds.
3. **Resolve links** on the map as loaded (before creatures are placed) — §5.
4. Reset: keys (4 colours) = 0, boots (4 kinds) = none, exit-reached = false, tank-reverse state = 0, death reason = none.
5. Restore toggle walls to their stored meaning if a previous attempt swapped them, and reset the socket to "closed".
6. **Place objects**: for every non-empty slot `i` (127 down to 0), compute its cell from (x/8, y/8); set the slot's *under-tile* to the map value at that cell and write `0x80 | i` into the map cell. **Exception:** if the cell is a **trap** (`0x2D`), additionally set the object's moving flag (it will be "pressing" to leave in its facing direction). A map byte of `0x80` or more in the level data itself is kept as it is and is an object reference from the start, whether or not slot `i & 0x7F` is there (a "ghost" reference; verified, doc 09 §25). Real levels never contain one.
7. Force Chip's direction to South (facing the player); Chip's moving flag clear.
8. Reset the random number generator state to 0 (doc 04 §9).
9. Game is now in the *waiting for first input* state (doc 05).

## 5. Link resolution (buttons → targets, teleport chain)

Links are computed once per attempt by scanning the map in reading order (cell 0 → 1023). For each source cell, search for its target starting from the neighbouring cell and **wrapping around** the 1024 cells:

| Source tile | Target tile | Search direction |
|---|---|---|
| Brown button `0x2E` | Trap `0x2D` | Forward (cell+1, +2, …) |
| Red button `0x30` | Clone machine `0x2F` | Forward |
| Teleport `0x0E` | Teleport `0x0E` | **Backward** (cell−1, −2, …) |

The first match is the link. Consequences:
- Each brown button controls the **next trap after it** in reading order; each red button the **next cloner after it**. Several buttons may share a target.
- A teleport sends to the **previous teleport** in reading order (the first teleport sends to the last one). A lone teleport links to itself.
- The original has no handling for a button without any matching target: the search never ends and the program **hangs while starting the level** (verified by injecting imported levels; a red button with no clone machine, or a brown button with no trap, anywhere on the map is enough). An implementation that wants to play such levels should treat the button as unlinked; one that reproduces the cartridge should report the level as unplayable.

Links are stored per source cell and never change during the attempt.

## 6. Passwords

Passwords are **not stored** in the ROM; they are generated at power-on by a deterministic pseudo-random generator.

### 6.1 Generator

16-bit state `(lo, hi)`, initialised to `(0, 0)`. One step (`next()`), using 8-bit unsigned arithmetic:

```
a  = lo >> 1
c  = bit 0 of a              # (= bit 1 of lo)
a  = a >> 1
a  = (a − lo − (1 − c)) mod 256 ; c = 1 if that subtraction did not borrow, else 0
c  = bit 0 of a
# rotate the 16-bit state:
c2 = bit 7 of hi
hi = ((hi << 1) | c) & 0xFF
lo = (lo >> 1) | (c2 << 7)
return lo XOR hi
```

(Precisely: shift `lo` right twice keeping the carry from the second shift; subtract `lo` with that carry as "no-borrow"; shift the difference right once; the shifted-out bit enters `hi` from the bottom while `hi`'s top bit enters `lo` from the top; output `lo ⊕ hi`.)

**Letter draw:** repeat `r = next() & 0x1F` until `r < 26`; letter = `'A' + r`.

### 6.2 Table construction

There are 256 password slots (only 0–149 meaningful), each 4 letters.

1. Seed `(lo, hi) = (0, 0)`.
2. Visit slots in the order **0, 255, 254, …, 2, 1**. For each, draw 4 letters (first letter first).
3. Then draw three more letters, which **replace the first letter** of slots **97, 106, 113** (0-based; levels 98, 107, 114), in that order.

Slot `L` (0-based) is the password of level `L + 1`. Check values: level 1 = `BDHP`, level 2 = `JXMJ`, level 3 = `ECBQ`, level 150 = `GNLP` (full list in doc 09).

### 6.3 Password entry

- Accepted passwords: levels 1–149 (slots 0–148). An entered code is compared against these in increasing order; the first match selects the level and resets the attempt counter.
- The special code `MAND` launches the secret overlay (doc 06 §9) instead.
- The entry field is pre-filled with the password of the current level (level 1 at power-on). Confirming an unknown code leaves the current level unchanged, so the game simply starts there ("press fire to begin").
