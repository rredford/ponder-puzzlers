# 08 — Audio

Confidence: §1–§3 verified; §4 (effect patch format and parameter mapping) analysed in detail; §5 (music format) structure analysed, some command details marked *partial*. See doc 10 for the follow-up list.

## 1. Hardware model (what the data drives)

The Lynx has **four identical audio channels**. Each is a 12-bit linear-feedback shift register (LFSR) clocked by its own programmable timer:

- **Timer**: a reload value (8 bits, "backup") and a clock prescale (1, 2, 4, 8, 16, 32 or 64 µs per count). Each underflow clocks the LFSR once.
- **LFSR**: the new input bit is the inverted XOR of a selectable set of taps (taps at register bits 0, 1, 2, 3, 4, 5, 7, 10 and 11). The tap set and the initial register contents select the waveform: a single tap gives a square wave; several taps give noise/buzz timbres.
- **Output**: in normal mode the channel outputs `+volume` when the output bit is 1 and `−volume` otherwise; in *integrate* mode each clock adds or subtracts `volume` to/from the running output (producing ramp/triangle-like shapes).
- **Volume**: signed 8-bit. The four channels are summed into an 8-bit DAC (mono on the original unit).

A faithful reimplementation emulates this model at ≥ 48 kHz; a simplified one can approximate effects with square/noise generators.

## 2. Driver timing

- Sound effects and music are updated by a periodic interrupt at ≈ **264.8 Hz** (one update every 3.776 ms).
- Sounds are **priority-allocated** to the four channels: starting a sound picks the channel whose current sound has the lowest priority value; the new sound takes it only if its priority is greater than or equal to that value. Free channels have priority 0. Music voices use channels through the same mechanism with their own priorities.

## 3. Sound-effect catalogue

18 effects (ids `00–11`). Patch pointers: low bytes MAIN `$2768`, high bytes `$277A`; priorities at `$2751`.

| Id | Priority | Triggered by |
|---|---|---|
| 00 | `65` | Picking up a key, boot or chip; pressing any button (green, blue, brown) |
| 01 | `66` | Stepping on a recessed wall |
| 02 | `67` | Thief takes the boots |
| 03 | `68` | Reaching the exit; entering a teleport |
| 04 | `69` | (not triggered by game logic) |
| 05 | `6A` | Door/socket opened (followed by 0B); cloning |
| 06 | `FA` | **Looping** ice-slide sound: started when Chip is on ice without skates, stopped when he leaves ice or the game stops running |
| 07 | `6B` | Boots in use: arriving on ice with skates / on a force floor with suction boots |
| 08 | `6C` | Bumping into an obstacle (once per bump); anything entering a trap |
| 09 | `6D` | Death: Chip killed by a monster or block, burned, or anything hitting a bomb |
| 0A | `6E` | (not triggered by game logic) |
| 0B | `6F` | Dirt / fake blue wall cleared; door/socket opened (after 05) |
| 0C | `70` | Splash (drowning, block into water); Chip deflected by an ice corner |
| 0D | `71` | (not triggered by game logic) |
| 0E | `FA` | **Looping** force-floor sound: while Chip is on a force floor without suction boots |
| 0F | `72` | Pushing a block |
| 10 | `73` | Walking into fire with fire boots |
| 11 | `74` | Swimming (entering water with flippers) |

Looping effects are owned by the game logic: it starts the loop when the condition becomes true and stops that channel when it becomes false (or when paused/dead/finished).

**Bump latch.** The bump sound (08) for Chip is gated by a latch: a blocked move requests 08 only when the latch is clear, and then sets it; any tick without joystick input clears it (holding against a wall does not repeat the sound; tapping again does). The latch is a single RAM byte that is never reset between levels or attempts. The title screen leaves it set, so a blocked first move of the first level played after the title makes no sound; after that it carries over (e.g. it is clear at the start of level 2 after level 1 is won). Traps and clone machines request 08 on arrival without the latch.

**Requests versus channels.** The table lists what the game *requests*. Whether a request is heard depends on §2: e.g. a bump right after a splash is refused when no effect channel holds a lower priority. Some patches loop back to their first record, so a channel can re-read a patch start without a new request.

**Verified on the original** (requests detected as reads of the priority table entry `$2751 + id`, compared tick for tick with a reimplementation): all Tile World replays of CC1 (148, about 72 000 requests), CCLP1 (149, about 30 000) and CCLP5 (97 that start, about 16 600) agree on every tick. Effects 04, 0A and 0D were never requested in any of them.

**Glitches that reach sound data** (doc 04 §4.4; of the 144 measured stray-write targets only two land in it, the rest are at least 450 bytes away): drawing odd tile `67` writes its screen position into the ice-slide patch (effect 06, bytes `$2952`–`$2955`), so the next slide sound plays with altered values (same length and timing); drawing odd tile `6C` writes into the end of music voice 3's instrument block (`$8194`–`$8197`), which audibly changes the music for that song. Neither affects play or stops the game (tested over 600 and 1200 ticks).

## 4. Effect patch format (keyframe envelopes)

A patch is a list of **records**. Times are absolute 16-bit update counts.

```
record:
  time      u16   time stamp of this record (driver updates since sound start*)
  flagsA    u8
  flagsB    u8
  [loopA    u8]   present if flagsB bit 7
  [loopB    u8]   present if flagsB bit 5
  [values]        up to 8 u16 fields, present per flag bits (order below)
  (next record follows; its `time` is the end time of this one)
```
\* The first record's time initialises the counter; each update increments it; when it equals the next record's time, that record is applied.

Parameter fields, in storage order, and the flag bit that marks each as present:

| # | Field | Present if |
|---|---|---|
| 1 | P1 = pitch period | flagsB bit 3 |
| 2 | P2 = LFSR initial contents (12-bit: low byte + high nibble) | flagsB bit 2 (see note) |
| 3 | P3 = tap selection | flagsB bit 1 |
| 4 | P4 = volume (high byte used) | flagsB bit 0 |
| 5 | ΔP1 per update | flagsA bit 7 |
| 6 | ΔP2 per update | flagsA bit 6 |
| 7 | ΔP3 per update | flagsA bit 5 |
| 8 | ΔP4 per update | flagsA bit 4 |

Note: the presence bits are taken from (flagsB low nibble, flagsA high nibble) as one 8-bit set in the order of the table; flagsB bit 2 additionally means "load P2 into the LFSR once at this record" (otherwise the LFSR free-runs).

Other flag bits:
- flagsA bit 0: **end of sound** — channel released.
- flagsA bit 2: reload the LFSR from P2 on *every* update.
- flagsA bit 3: integrate mode on.
- flagsB bit 7 / bit 6: loop A *start* (with repeat count) / loop A *end* (jump back to start while the count runs).
- flagsB bit 5 / bit 4: loop B start / end (a second, independent loop).

Every update: each present Δ is added to its parameter (16-bit, wrapping); the hardware is then programmed from P1–P4:
- **P1 → LFSR clock period** in units of ¼ µs, as a floating-point pair: shift P1 left until bit 15 is set, at most 6 times (`s` shifts); **reload = high byte of the shifted value**, **prescale = 2^(6 − s) µs** (64 µs when no shift is needed, down to 1 µs). The resulting period ≈ P1/4 µs (8-bit mantissa precision); larger P1 ⇒ lower pitch.
- **P2 → LFSR contents** (when loaded): 12-bit value = `P2 & 0x0FFF` (low byte + low nibble of the high byte).
- **P3 → taps**: P3 bits 4–9 select taps 0–5; P3 bit 11 selects tap 7; P3 bits 14 and 15 select taps 10 and 11. Other bits are unused.
- **P4 → volume**: the high byte of P4 is the channel volume (signed).
- Integrate mode (flagsA bit 3) is applied together with the prescale.

## 5. Music format (files 3–17)

*Structure verified; some command bits partial.*

### 5.1 Song header
| Offset | Size | Meaning |
|---|---|---|
| 0–7 | 8 | Zero in the file (workspace; the driver writes the voice start pointers here) |
| 8 | 1 | Number of voices `n` (1–4) |
| 9 | 2·k | **Pattern table**: 16-bit offsets relative to the song start. Entries 0…n−1 are the start patterns of voices 0…n−1; further entries are sub-patterns and one-shot effects referenced by commands |

All pointers inside a song are offsets from the song's first byte.

### 5.2 Voice state
Each of the (up to) four voices has: a sequence pointer, a current **pitch table** pointer (16 × u16 pitch values, i.e. P1 periods), a current **duration table** pointer (8 × u16 lengths in driver updates), a gate setting, a two-level call stack, two loop counters, and a **voice block** of 0x36 bytes:

| Voice-block offset | Content |
|---|---|
| `+0x00` | Voice priority (voice 0 = `E0`, 1 = `A0`, 2 = `60`, 3 = `20`) |
| `+0x02` | **Instrument**: an effect patch (§4) of five records — R0 at `+0x02` (sets P1–P4 and ΔP1/ΔP3/ΔP4), R1 at `+0x14`, R2 at `+0x1E`, R3 at `+0x28`, R4 at `+0x32` (end record). R1–R3 carry only deltas, so the instrument is a 4-stage envelope (attack, decay, sustain, release) |

When a note plays, the driver writes the note's pitch into R0's P1 (`+0x06`), the note length into R4's time (`+0x32`), and the release point into R3's time (`+0x28`); if R2's (and then R1's) time would not precede the release point it is temporarily pulled back to just before it, and restored for the next note.

Because voice priorities are compared with effect priorities (§2–§3), **ordinary effects (65–74) can take channels from voices 2 and 3 only**, while the looping ice/force sounds (FA) can take any channel.

### 5.3 Events
- **Note byte** (bit 7 clear): `pitch = byte & 0x0F` (index into the pitch table), `length = (byte >> 4) & 7` (index into the duration table). The next event is read after `length` updates. The note's release point is `length − gate_value`, or `gate_value` itself in fixed-gate mode.
- **Command** (bit 7 set): a `cmd` byte and an `ext` byte, followed by the operands of the set bits **in this order**:

| Order | Byte/bit | Operand | Meaning |
|---|---|---|---|
| 1 | ext bit 3 | u8 pattern# | **Call** sub-pattern; when it ends, execution resumes at this same command with the call skipped (two nesting levels) |
| 2 | ext bit 4 | — | **Loop B end**: if the loop-B counter is non-zero, decrement; jump back to the loop-B start while it stays non-zero. A counter of 0 loops forever |
| 3 | ext bit 6 | — | **Loop A end** (same rules) |
| 4 | ext bit 7 | u8 count | **Loop A start**: remember this command and the count (not re-armed when jumped back to) |
| 5 | ext bit 5 | u8 count | **Loop B start** |
| 6 | ext bits 1–0 | u16 | **Gate**: bit 0 set → fixed release time = value; else release = length − value |
| 7 | cmd bit 5 | u8 pattern# | **One-shot**: play pattern-table entry `pattern#` as an effect patch on this voice (replaces the voice's sound until its next note) |
| 8 | cmd bit 4 | 1 byte | Skipped (unused operand) |
| 9 | cmd bit 3 | u16 offset | Set duration table |
| 10 | cmd bit 2 | u16 offset | Set pitch table |
| 11 | cmd bit 1 | list | **Instrument edit**: entries `(0x80 \| k, u16 value)` write `value` at byte offset `k` of the voice block, until a byte < 0x80 (which is not consumed) or `0xFF` (consumed). If the first byte is `0xFF`, eleven instrument words are cleared (offsets `08 0C 0E 10 18 1A 22 24 26 2C 2E`) |
| 12 | cmd bit 0 | — | **End of pattern**: return from a call, else the voice stops |

Commands without the end bit are followed directly by the next event.

Muting (Option 2 / pause) suppresses note starts (sequencing continues so the music stays in time).

### 5.4 Track assignment
Level music: file `3 + (index of 3rd password letter >> 1)` (doc 01 §7). Title: file 16. Ending: file 17. Music is restarted at each level attempt.

## 6. Reimplementation options

1. **Faithful**: implement the 4-channel LFSR synthesizer (§1) and a driver following §2–§5, fed by the extracted patch/song data from the user's ROM.
2. **Simplified**: map the 18 effects to short synthesized or newly recorded sounds and use new music; keep the trigger rules of §3 (including looping ice/force sounds) for the right game feel.
