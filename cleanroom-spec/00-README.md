# Chip's Challenge (Atari Lynx) — Clean-Room Specification Set

**Status:** v1.0 (first full pass) · **Subject:** `Chip's Challenge.lnx` (Lynx cartridge image, 128 KiB + 64-byte LNX header) · **Target:** a new, independently written implementation that runs natively on Linux.

## 1. What these documents are

These documents describe *what the original game does*, not *how its code is written*. They were produced by a "dirty" analysis team that examined the cartridge image (unpacking it, running it in an instrumented emulator, and reading its machine code). They are meant to be handed to a separate "clean" implementation team that **never looks at the ROM's code**.

The documents deliberately contain:

- Facts about data formats (byte layouts, compression scheme, tables of functional constants).
- Behavioural rules of the game (tile semantics, creature AI, timing, scoring, UI flow), written as prose, tables and freshly written pseudocode.
- Locations of data inside a user-supplied ROM so that an *asset extractor* can pull graphics, levels, text and music from the user's own cartridge image at install/run time.

They deliberately do **not** contain:

- Disassembly, code listings, or translations of original routines.
- Copies of copyrighted content: level layouts, graphics, the story text, credits text, music data. The reimplementation must read these from the user's own ROM file (or substitute original/free content).

## 2. Document map

| # | Document | Covers |
|---|----------|--------|
| 01 | Cartridge, file system & compression | LNX header, cart addressing, boot chain (what can be ignored), file directory, BPE decompression, role of every file |
| 02 | Level data format & passwords | 32×32 map, creature table, time limit, title/hint text, link resolution (buttons/teleports), password generator, level numbering, special files |
| 03 | Tile catalogue & rules | All 52 tile codes: names, passability masks, on-enter / on-stand behaviour, special mechanics |
| 04 | Objects, movement engine & creature AI | Object table model, state byte, tick order, movement/collision algorithm, sliding, pushing, teleport, trap, cloner, each monster's AI, speeds |
| 05 | Player control, game loop, timing & scoring | Input → direction selection, force-floor override, frame pacing (20 ticks/s), clock, death/finish, attempts, scoring, skip-level offer |
| 06 | Presentation & UI flow | Screens and state flow, HUD layout, camera/viewport, draw order, animations, control mapping, charset & font, message catalogue (by function) |
| 07 | Graphics asset extraction | Lynx sprite (SCB) format and decoder, palette format, where each tile/creature/HUD sprite and palette lives in the ROM |
| 08 | Audio | Sound-effect catalogue & triggers, channel/priority model, music track assignment, data formats (as far as analysed), Lynx audio channel model, open items |
| 09 | Verification vectors | CRCs/sizes of every decoded file, password sample, level-1 facts — to let the clean team test their extractor without seeing the ROM internals |
| 10 | Open questions & confidence | What is verified, what is inferred, what still needs analysis |

## 3. Conventions used throughout

- **Hex** is written `$xx` / `$xxxx` or `0x..`. Multi-byte integers in ROM data are **little-endian** unless stated.
- **"Cart offset"** = byte offset into the cartridge body *after* removing the 64-byte LNX header.
- **"File N"** = entry N of the cartridge's file directory (doc 01). After decompression each file has a natural *load address* on the Lynx; internal pointers in a file are expressed as Lynx RAM addresses. For extraction: `file_offset = address − load_address`.
  - **MAIN** = File 2 (main program), load address `$1C6E`. Most sprite tables, palettes and text live here.
  - **GFX0** = File 0, load address `$A7C0`.
  - **LEVEL** = one level file, load address `$0C00`.
- **Directions**: `0 = North (up)`, `1 = East (right)`, `2 = South (down)`, `3 = West (left)`. "Turn right" = `+1 mod 4`, "turn left" = `+3 mod 4`, "reverse" = `+2 mod 4`.
- **Coordinates**: map cells are `(col, row)`, 0..31 each; cell index = `row*32 + col` ("reading order"). Object positions are in **sub-tile units of 1/8 tile** (one tile = 8 units).
- **Tick** = one game-logic update (≈20 per second, doc 05).
- Original names of tiles/creatures are the conventional Chip's Challenge names; the codes are this cartridge's own.

## 4. Recommended architecture for the reimplementation

1. **Extractor** (docs 01, 02, 07, 08, 09): reads the user's `.lnx`, validates it (doc 09), decompresses files, emits: level set (JSON or binary), tile/creature sprite sheets (PNG), font, palettes, text strings, music/SFX data.
2. **Engine** (docs 03, 04, 05): a deterministic tick-based simulation reproducing the Lynx rules exactly (including quirks), independent of rendering frame rate.
3. **Front-end** (docs 06, 08): SDL2 (or similar) window, scaled 160×102 logical display, keyboard/gamepad input, an audio synthesizer modelled on the Lynx's four LFSR channels (or a simplified substitute).

## 5. Provenance & method (for the record)

The analysis was done with tools written for this purpose: a cartridge/directory reader, an independent decompressor (validated byte-for-byte against the original loader running in emulation), a 65C02 emulator with enough Lynx hardware (cart port, timers/IRQ, sprite engine, math unit) to run the game to the title, story and level screens, and table dumps. Rules in docs 03–05 were derived from the game logic and then verified in lock-step against the original: all 144 Tile World solution replays (levels 1–144) matched tick-for-tick (doc 10 §2, doc 09 §6).
