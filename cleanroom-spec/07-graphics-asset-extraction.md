# 07 — Graphics Asset Extraction

All graphics are stored as Lynx hardware sprites: a **sprite control block (SCB)** that references compressed **sprite data**, plus a 16-colour **palette**. The extractor should implement the decoder below, render each needed SCB into an RGBA image using the right palette, and write sprite sheets. Addresses are Lynx RAM addresses; convert to file offsets with the file's load address (MAIN `$1C6E`, GFX0 `$A7C0`, screen files `$9000`). SCB fields that are themselves addresses (next SCB, data) point into the same address space.

## 1. SCB layout

| Offset | Size | Field |
|---|---|---|
| 0 | 1 | **CTL0**: bits 7–6 = bits-per-pixel − 1 (1–4 bpp); bit 5 = horizontal flip; bit 4 = vertical flip; bits 2–0 = sprite type |
| 1 | 1 | **CTL1**: bit 7 = *literal-only* data; bits 5–4 = reload depth (0: none, 1: size, 2: size+stretch, 3: size+stretch+tilt); bit 3 = keep previous palette (no palette bytes follow); bit 2 = skip this sprite; bits 1–0 = start quadrant |
| 2 | 1 | Collision number (ignore) |
| 3 | 2 | Next SCB address (LE). A zero **high byte** ends the chain |
| 5 | 2 | Sprite data address (LE) |
| 7 | 2 | Horizontal position (signed LE) |
| 9 | 2 | Vertical position (signed LE) |
| 11 | 0/4/6/8 | Per reload depth: H-size, V-size (8.8 fixed, `0x0100` = 1:1), stretch, tilt (each 2 bytes) |
| … | 0/1/2/4/8 | Palette (pen map) unless CTL1 bit 3: `2^bpp / 2` bytes; each byte holds two 4-bit colour indices (high nibble = even pen). Pen *p* of the sprite is drawn with colour `map[p]`. |

Sizes and the pen map persist from the previous SCB of a chain when not reloaded. All game tiles and creatures use reload depth 0 (size 1:1).

**Sprite types used here:** type 1 (background, *opaque*: pen 0 is drawn) for all map tiles and the pushable block; type 5 (normal, *pen 0 transparent*) for creatures, Chip, effects and text. Treat types 0–1 as opaque and 2–7 as pen-0-transparent.

## 2. Sprite data

The data is a list of **lines**:

- Each line starts with an **offset byte** `N` = length of the line in bytes including itself.
  - `N = 0`: end of sprite.
  - `N = 1`: end of quadrant — continue with the next quadrant (see §2.2).
- The `N − 1` bytes that follow form a bit stream read **most-significant bit first**.

### 2.1 Line bit stream
- **Packed mode** (CTL1 bit 7 clear): a series of packets, each `1 bit flag + 4 bit count c`:
  - flag 1 (literal run): `c + 1` pixels follow, `bpp` bits each.
  - flag 0 (repeat run): if `c = 0` the line ends; otherwise one `bpp`-bit pixel follows, repeated `c + 1` times.
  - The line also ends when its bytes are exhausted.
- **Literal-only mode** (CTL1 bit 7 set): consecutive `bpp`-bit pixels until the line's bytes are exhausted. (Used by text sprites built at run time; not needed for extraction.)

### 2.2 Quadrants
Drawing starts at the SCB position in the *start quadrant* and changes quadrant at each `N = 1` marker, cycling 0→1→2→3: quadrant 0 = rightwards & downwards, 1 = rightwards & upwards, 2 = leftwards & upwards, 3 = leftwards & downwards. Every quadrant starts again at the origin row/column (upward quadrants begin on the row above the origin, leftward ones on the column left of it). Flip bits invert the respective direction. Tiles use only quadrant 0; a few creature frames (e.g. the Blob's stretched frames) also draw in other quadrants and therefore extend above/left of the origin.

### 2.3 Scaling
Each source pixel/line adds the H/V size to an accumulator; the integer part (units of `0x100`) is the number of screen pixels/rows to emit, the fraction carries over. At `0x0100` this is 1:1.

The decoder described here reproduces all 52 tile sprites, 240 creature frames, 18 effect frames and the title/story/ending screens correctly.

## 3. Palette format

32 bytes for colours 0–15: bytes 0–15 = **green** (low nibble); bytes 16–31 = **blue** (high nibble) and **red** (low nibble). Expand each 4-bit value `v` to 8 bits as `v × 17`.

| Palette | Location |
|---|---|
| In-game (levels, story pages, password screen) | MAIN `$7637` |
| Title / attract | GFX0 `$A7C0` (first 32 bytes of file 0) |
| Ending | MAIN `$856C` |

## 4. Where the game sprites are (MAIN)

| Asset | Table | Indexing |
|---|---|---|
| Map tiles (default frame) | `$2DBB`: 52 × 16-bit SCB addresses | tile code `0x00–0x33` |
| Creatures & Chip | low bytes `$2BDB`, high bytes `$2CCB` (240 entries) | `index = (state & 0x3F) × 4 + frame` where `state & 0x3F = type × 4 + direction` and `frame` 0–3 (doc 06 §5) |
| Chip alternate pose | same table | Chip index computed with `state + 0x2C` |
| Chip pushing poses | same table | `state + 0x30` and `state + 0x34` |
| Effects | low `$2BB7`, high `$2BC9` (18 entries) | frame number `0x00–0x11` (explosion 0–5, Chip death 6–11, splash 12–17) |
| Inventory icons | the tile sprites of `1E 1F 20 21` (keys) and `0F 11 10 12` (skates, suction, fire boots, flippers) | |

Entries 0–15 of the creature table (type 0) duplicate Chip and are unused. The block (type 7) is opaque, all other creature frames are transparent.

Tiles are 12 × 12 pixels with their origin at the top-left of the cell (three tiles — thin walls/corners — overhang by one pixel). Creature frames are nominally 12 × 12 at the same origin, but a few extend up to ~6 px beyond the cell on any side; extract creatures into e.g. 24 × 24 cells with the cell origin at (6, 6) and draw them with that offset.

## 5. Animated tiles (MAIN)

The game animates tiles by swapping SCB pointers or palette bytes each tick. Extract every frame:

| Tile(s) | Frames (SCB addresses) | Timing |
|---|---|---|
| Exit `25` | words at `$2F3B` (3) | frame k for 2 ticks, cycle 6 ticks, played 3→2→1 |
| Water `14` | words at `$2F41` (3) | same |
| Fire `13` | words at `$2F47` (3) | same |
| Teleport `0E` | words at `$2F4D` (3) | same |
| Toggle wall closed / open | words at `$2E5B`: 4 "closed" frames then 4 "open" frames | 1 frame per tick, 4-tick cycle. Tile `18` shows the closed set and `17` the open set until the green button swaps them |
| "Random" force floor `09` | words at `$2E53`: the N, E, S, W force-floor SCBs | changes every 2 ticks, shown in order W, S, E, N |
| Force floors `05 06 07 08` | static SCBs, **palette bytes 1 and 2** (pens 2–5) replaced each tick, 4 phases | see below |

Force-floor palette phases (`p = 0…3`, advancing every tick; values are the two pen-map bytes):

| Floors | byte 1 for p = 0,1,2,3 | byte 2 for p = 0,1,2,3 |
|---|---|---|
| North `05`, East `06` | `12 51 35 23` | `35 23 12 51` |
| South `07`, West `08` | `12 23 35 51` | `35 51 12 23` |

(North/South share one image, East/West another; the opposite rotation order makes the stripes flow in opposite directions.)

## 6. Font and text (MAIN)

| Asset | Location / format |
|---|---|
| Font | `$4630`: 7 bytes per glyph for codes `01–31`; glyph of code `c` at `$4630 + 7(c − 1)`. Byte 0 is the **bottom** row; bit 7 is the leftmost pixel; 8 × 7 pixels |
| Story pages | page pointers: low bytes `$1E19`, high bytes `$1E2B` (18 pages). Each page: lines terminated by `00`, page ends at an empty line |
| UI messages | pointers: low `$33C1`, high `$33CD` (12 entries, ids as doc 06 §7); each a list of `00`-terminated lines ending at an empty line (only the first line is used for M1–M5) |
| Praise lines | pointers: low `$3407`, high `$340C` (5 entries); attempt thresholds `$3411` = `01 03 05 0A FF` |
| Story-page schedule | 18 bytes at `$1E3D` (level index that triggers page k; `00` = not scheduled) |
| Level titles / hints | in each level file (doc 02) |

Some UI strings contain placeholder characters (e.g. `X…X` digit fields, `CODE` letters) that the game overwrites at run time; the reimplementation should render its own values.

## 7. Title, attract and ending screens

These are SCB chains in MAIN whose data lives in GFX0 (title background, sparkles) or in files 18–20 (loaded at `$9000`). Known chain heads: title circuit-board background `$8D40` (MAIN, data in GFX0); title/credits piece descriptors start around `$8C3C`; ending chains are listed in two word tables at `$8364` and `$8396`. Because the choreography is non-essential, the recommended approach is: render each referenced SCB once into PNGs and build a simplified sequence (doc 10 lists this as partially analysed).

## 8. Suggested extractor outputs

- `tiles.png` — 52 tiles (+ animation frames) at 12 × 12.
- `creatures.png` — 60 groups × 4 frames (24 × 24 cells, origin at (6,6), alpha).
- `effects.png` — 18 frames.
- `font.png` — 49 glyphs 8 × 7.
- `palettes.json` — the three palettes as RGB.
- `screens/*.png` — title/ending artwork.
