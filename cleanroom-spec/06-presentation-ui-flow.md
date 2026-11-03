# 06 — Presentation & UI Flow

## 1. Display

- Logical screen **160 × 102** pixels, 16 colours from a 4096-colour (4-4-4 RGB) palette, ≈ 59.9 Hz. The game redraws once per tick (every 3 frames, ≈ 20 fps) with double buffering.
- Recommended PC presentation: integer-scaled 160×102 (e.g. ×6 = 960×612), nearest-neighbour, optional 180° flip setting.

## 2. Screen / state flow

```
power-on
  └─► TITLE / ATTRACT (title music; loops until A or B)
        └─► STORY pages 0, 1, 2 (A/B advances each)
              └─► PASSWORD ENTRY (pre-filled with the current level's code)
                    ├─ "MAND" ─► secret overlay (§9)
                    └─► LEVEL START ─► [SKIP OFFER?] ─► LEVEL INTRO overlay (waiting for first input)
                                         └─► PLAY ⇄ PAUSE
                                               ├─ finished ─► SCORE TALLY ─► [STORY page] ─► next LEVEL START
                                               ├─ dead ─────► DEATH message ─► same LEVEL START
                                               ├─ Option 1 ─► same LEVEL START
                                               └─ Pause+Option 1 ─► TITLE / ATTRACT
  level slot 145/150 (end marker) ─► ENDING (loops)
```

- Before showing a screen that waits for A/B, the game first waits until all buttons have been released (≈ 100 polls), so a held button never skips a screen.
- "A/B" confirmation is edge-detected with the auto-repeat helper below.

**Button helper (menus):** a poll reports "pressed" when the joystick state is unchanged since the previous poll for the first time (i.e. after one stable poll); while held, it repeats after 10 polls and then every 3 polls. Menus act on directions and A/B through this helper.

## 3. Story pages

- 18 text pages (index 0–17). Pages 0, 1, 2 are shown at the start of a new game. Page *k* (3 ≤ k ≤ 16) is shown when the game advances to level index `10 × (k − 2)` (i.e. before levels 11, 21, …, 141). Page 17 is not scheduled by this table.
- A page is a list of text lines (each `0x00`-terminated, list ends with an empty line); up to 8 lines are shown, centred, 12 px apart, on a plain background; A/B continues.
- The text itself is copyrighted story content: **extract it from the ROM** (doc 07 §6) or write new text.

## 4. In-game screen

```
 ┌──────────────── 102 px ──────────────┬──── 58 px ────┐
 │                                       │  LEVEL        │
 │   map viewport: 8.5 × 8.5 tiles       │   nnn         │
 │   (12×12 px tiles), Chip centred      │  TIME:        │
 │                                       │   nnn         │
 │                                       │  CHIPS        │
 │                                       │  LEFT:        │
 │                                       │   nnn         │
 │                                       │ ┌──────────┐  │
 │                                       │ │ R  B  Y  G│ │  keys row
 │                                       │ │ Sk Su Fi Fl│ │  boots row
 │                                       │ └──────────┘  │
 └───────────────────────────────────────┴───────────────┘
```

- **HUD** (right panel, drawn over the map): labels and three 3-digit numbers (level number, time left or `---`, chips left). When chips left is 0 its number flashes (alternates colour every 4 ticks).
- **Inventory box** (bottom of the panel): one icon per key colour held (red, blue, yellow, green — left to right, top row at screen y ≈ 73) and per boot owned (skates, suction boots, fire boots, flippers — bottom row at y ≈ 85); icons are the corresponding tile graphics, 12 px apart starting at x ≈ 107. Key *counts* are not shown, only presence.
- **Overlays** are centred text lines drawn over the play field (§6).

### 4.1 Camera

Positions are tracked in quarter-tiles (`q = x/2` for an object position in 1/8-tile units).
- Camera `(cx, cy)` in quarter-tiles: `cx = clamp(qx_chip − 16, 0, 93)`, same for y. Recomputed every tick, no smoothing — the view scrolls in 3-pixel steps as Chip moves.
- A map cell `(col, row)` is drawn at screen `(12·col − 3·cx − 3, 12·row − 3·cy − 3)`; an object at `(3·(x/2 − cx) − 3, 3·(y/2 − cy) − 3)`. Chip is therefore drawn at (45, 45) except near map edges. The visible map area is x, y ∈ [0, 102).
- 11 × 11 cells around the camera are drawn each frame; cells outside the map are drawn as the tile of cell 0.

### 4.2 Draw order
1. Map tiles (for cells holding an object, its *under* tile).
2. Objects, in reading order of their cells (top-left first), so lower/right objects overlap.
3. HUD panel, numbers, inventory icons.
4. Overlay text (intro / pause / hint / death / score).

## 5. Animation

| Element | Rule |
|---|---|
| Creature walk cycle | Sprite = `[type, direction, frame]`, `frame = (x | y) >> 1 & 3` — i.e. the frame advances with each 2-unit step (4 frames per tile) |
| Chip extra poses | When the tick counter has bit 2 set, Chip uses his alternate pose set; while "pushing/straining" (a tried move was blocked or a block was pushed) he uses the pushing pose set, alternating between two pushing sets with tick bit 2 |
| Effects | Explosion, Chip-death, splash: 6 frames each, advancing on odd ticks (doc 04 §8) |
| Exit, water, fire, teleport | 3-frame loops; frame changes every 2 ticks (6-tick cycle; frames shown in order 3, 2, 1) |
| Force floors N/S/E/W | Palette rotation (4 phases, advancing every tick); N/S and E/W floors use different phase tables (doc 07 §5) |
| "Random" force floor | Shows the four force-floor looks in turn (W, S, E, N), changing every 2 ticks |
| Toggle walls | 4-frame "marching" outline (open and closed versions), advancing every tick; open/closed graphics swap when the green button is pressed |
| Chips-left number | Flashes when zero |

Tile animation counters run every loop iteration, including while paused or waiting.

## 6. Text system

### 6.1 Character set (used by level titles, hints, story, UI)

| Code | Char | Code | Char |
|---|---|---|---|
| `00` | end of line | `26` | `!` |
| `01` | space | `27` | `"` |
| `02–0B` | `0`–`9` | `28` | `'` (also used as quote mark) |
| `0C–25` | `A`–`Z` | `29` `2A` | `(` `)` |
| | | `2B` `2C` `2D` | `,` `-` `.` |
| | | `2E` `2F` `30` | `:` `;` `?` |
| | | `31` | solid/checker block (cursor) |

### 6.2 Font
8 × 7 pixel 1-bit glyphs, one per code `01–31` (doc 07 §6 for location). Text is upper case only.

### 6.3 Rendering
- Each line is centred horizontally on x = 80 (width = 8 px × characters).
- Drawn as an outlined text: four copies offset by one pixel (left, right, up, down) in a dark colour, then the main copy in a bright colour (yellow in-game). Some overlays draw their first line in an alternate colour.
- Line pitch 12 px. Multi-line blocks stop at an empty line or after 8 lines.

## 7. Message catalogue (by function)

Strings are stored in the ROM in the game charset (doc 07 §6 gives the tables). Short UI strings, by function:

| Id | Shown when | Content |
|---|---|---|
| M0 | Level finished | Praise line chosen by attempts (doc 05 §5), then M10 |
| M1 | Chip died | "Oops"-style death line |
| M2 | Time ran out | "Out of time" line |
| M3 | Paused | "Paused", followed by the level title (M4) and code (M5) |
| M4 | Level intro / pause | The level title (from the level file) |
| M5 | Level intro / pause | `CODE:` + the level's password |
| M8 | Skip offer | Four-line question + `YES  NO` choice line |
| M9 | Password entry | Four-line prompt ("please enter the code of the starting level or press fire to begin") + `CODE:xxxx` line with a cursor under the selected letter |
| M10 | Score tally | Four lines: time bonus (4 digits), level bonus (5), level score (5), total score (7) |
| M11 | Level intro | Total score line (7 digits) at the top of the screen |
| Hint | Chip stands, aligned, on a hint tile | The level's hint lines (from the level file) |

Intro overlay (while waiting for the first move): M11 at the top, M4 and M5 in the middle. Pause overlay: M3, M4, M5.

### 7.1 Password entry screen
Four letter slots, pre-filled. Left/right move the cursor (clamped 0–3), up increments the letter (Z wraps to A), down decrements (A wraps to Z); A/B confirms (doc 02 §6.3).

### 7.2 Skip dialog
Cursor under YES (left) or NO (right, default); left/right moves; A/B confirms (doc 05 §7).

## 8. Title, attract mode and ending

- **Title / attract**: circuit-board background (GFX0) with twinkling sparkles; title, a large Chip figure and scrolling credit pieces assembled from file 18 graphics; title music (file 16). Loops until A or B.
- **Ending** (when an end-marker level slot is loaded): ending music (file 17); a sequence that alternates two illustrated scenes (files 19 and 20) with tile-wipe transitions and short waits, looping. A/B leaves the ending loop, which reloads the same marker slot (so the ending repeats); Pause + Option 1 returns to the title.
- The reimplementation may recreate these sequences freely; exact choreography is non-essential (see doc 10).

## 9. Secret overlay

Entering the password `MAND` loads file 21 over part of the main program and runs it: a self-contained **Mandelbrot / Julia set explorer** (on-screen parameters for X, Y, step, depth, palette, cycle rate, and Julia constants). It is unrelated to the game and optional for a reimplementation.

## 10. Audio hooks
Music starts per level (doc 01 §7), title/ending music as above; the music toggle (Option 2) and pause mute it. Sound effects are listed in doc 08.
