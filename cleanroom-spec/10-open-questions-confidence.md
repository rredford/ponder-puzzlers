# 10 — Confidence, Quirks & Open Questions

## 1. How the specification was verified

| Area | Method | Confidence |
|---|---|---|
| Directory, BPE decompression | Independent decoder (written from doc 01) matches the original loader byte-for-byte; all 170 compressed files consume exactly their stored size; CRCs in doc 09 | **Verified** |
| Level format, link rules, passwords | Independent extractor (doc 02 only) reproduces all 150 passwords and all level facts | **Verified** |
| Tile rules, movement engine, AI, Chip control, clock | Lock-step comparison against the original on 148 cartridge-level and 149 imported-level solution replays plus random/synthetic tests (§2) | **Verified** |
| Sprite format, palettes, sprite tables | Decoder renders all tiles, creatures, effects, title/story/ending screens correctly | **Verified** (multi-quadrant edge conventions: high) |
| UI flow, messages, scoring | Read from program logic; key screens confirmed in emulation (title, story page, level intro/HUD, ending) | High |
| Audio | Effect catalogue/trigger sites verified; patch and music structure analysed from the driver | Medium (details in §4) |

## 2. Lock-step results

Two independent comparison campaigns were run. In both, the original program runs in emulation and an engine written only from docs 03–05 runs beside it; after **every tick** the entire world state is compared (32×32 map, all 128 object slots with state/position/under-tile, keys, boots, chips left, clock, finished flag).

**A. Tile World solution replays — 148 levels.** Every solution in the supplied `CC1.dac.tws` (levels 1–144 and bonus levels 146–149) was replayed in full: **148/148 matched tick-for-tick to the end, zero divergences**, over roughly 450 000 ticks in total (the longest single replay is about 22 700 ticks). On the original these end in 105 wins, 29 deaths, 1 time-out and 13 stalls (with the level started at tick 0 even when the first move comes later, and the random-force-floor counter set from each solution's slide value; doc 09 §6). The non-wins are Tile World ruleset differences, and the doc-engine reproduces each of them on the same tick (per-level table in doc 09 §6).

**B. Random-input and synthetic tests.** Random input on 20 real levels, plus synthetic "test rooms" (custom maps injected into the original after level load) for ice, force floors, teleports, traps/cloners/toggles, blocks, a monster zoo, an item field and a door/socket/wall/bomb room. All runs matched until Chip died, the level was finished, or 400–500 ticks elapsed.

**Errors these tests found and fixed in the docs:**
1. The socket opens at the start of the iteration *after* the last chip is collected (doc 03 §3.7).
2. Dirt, fake blue wall, doors and the socket turn into floor for *any* object standing on them, not just Chip (doc 03 §3.7, §3.9). Found in level 135, where a Bug starts on a fake blue wall.
3. The exact timing of Chip's removal on finishing (doc 05 §7).

**D. Imported levels injected into the original — CCLP1 (149 levels).** Each level of the community set CCLP1 was converted to the cartridge level format (strict mode of the remake: reading-order wiring, north/west thin walls moved to the neighbouring edge, at most 128 objects, MSCC-only tiles → wall), written into the emulated cartridge in place of level 1, and its Tile World (Lynx) solution replayed in lock-step against an engine written from these docs. Before the comparison, CC1 was put through the same injection path and reproduced all 148 table results (doc 09 §6) exactly. **CCLP1: 148/149 matched tick-for-tick to the end**; on the original they end in 59 wins, 61 deaths, 1 time-out and 27 stalls. The last one, level 140, makes the original **crash** at tick 652 (a ball wanders off the bottom edge onto stray state bytes, §3 item 8) — the end of what a description can reproduce, but the remake's engine reaches the same crash on the same tick when given the cartridge's own tables. Tile World itself wins all 149 in its Lynx mode; the difference is Tile World's, e.g. after a blocked move the original ignores the next tick's input (doc 05 §2), which CCLP1 level 1 depends on.

These levels exercise open map edges, which no cartridge level does, and found three gaps (now fixed):
4. **Blue keys are destroyed by any object other than Chip** that arrives on or stands on them (doc 03 §3.8).
5. **No bounds checks at the map edge**: off-map moves address the RAM around the map, coordinates wrap per axis (doc 04 §4.2).
6. **The decision phase dispatches on the slot's type**, not on the slot number (doc 04 §2) — visible only when stray writes change a slot's type.

**E. More imported sets — CCLP5 (100 levels; Chipster1059's CCLP5 submission file, not the released pack — see doc 09 §8) and geo5-1 / geo5-2 / geo5-5 (9 + 9 + 10).** Same method as D. **The geo sets: 28/28 matched tick-for-tick to the end. CCLP5: 94/100 matched to the end**; the other six (levels 2, 5, 10, 28, 31, 34) all diverge only after objects have left the map and written into the RAM around it, i.e. in the region §3 item 8 already marks as beyond a description — and in all six the remake, given the cartridge's tables, reaches the original's outcome on the same tick. On the original CCLP5 ends in 23 wins, 48 deaths, 1 time-out, 14 stalls and **14 crashes/hangs**; three of those (levels 22, 51, 63) hang at tick 0 because a button has no target (doc 02 §5). These runs added the failure table of doc 04 §4.3 (display hang, removal probe order, default death reason, odd types).

Tile World (Lynx mode) wins 99/100 CCLP5 and 26/28 geo levels. Where the remake's *extended* mode (Tile World's level semantics: DAT wiring, north/west thin walls kept, solid edges) parts from Tile World earlier than the strict conversion does, the cause found in every case examined (CCLP5 28, 6, 35, 62, 64) is a Blob or Walker: their direction comes from the RNG (§10 of doc 04), and a single extra thin wall or a different button wire changes which way they go. That is a Tile World difference (its random monsters do not follow the cartridge's RNG), not an engine fault.

**F. Off-map behaviour, measured (doc 04 §4.4).** Everything the original reaches only through off-map writes — tile codes `34`–`7F`, object references used as tiles, stray object types 0 and 12–15, effect frames `12`–`3F`, corrupted button/teleport links — was measured by black-box tests: about 7 000 short test levels, each observed on the original, never reading program bytes. An engine built from the resulting tables then matched the original in **3028 of 3038 lock-step scenarios**; the 10 exceptions were display effects (drawing an odd code next to Chip), since resolved (campaign H: 3038/3038). With these tables, **every imported-level oracle matches without any cartridge data**: CCLP1 149/149, CCLP5 100/100, geo5-1/2/5 9/9, 9/9, 10/10 (before: 148/149 and 93/100). The measurements corrected two assumptions of §4.2: seven codes in `34`–`67` are special (unenterable), and the leave check goes through the class mask (doc 04 §4.4).

**H. Display effects analysed (doc 04 §4.4).** Drawing an odd tile or a junk object writes the item's screen position to a fixed per-code address and then draws a garbage sprite; this explains every display effect seen. Chip drawn in a junk state is now tabulated (crash delay per value and tick parity), which turned 4 of the 5 remaining MS-set differences into exact matches (Jacques 986/986, Joshie then 1324/1325, now 1325/1325). The 76 odd tile codes are now grouped by where their write lands (doc 04 §4.4 table): 59 have no effect on play, 14 write into links, entry masks or slot tables, and 3 crash. The tile writes are now reproduced value for value (camera, window, order and the three crash rules), matching 2858 of 2869 random lock-step scenarios. Stray objects drawn are tabulated too (two states write game data: one re-aims slot states, one shifts the cell lookup's row table — Joshie 511 now matches). Open: crashes from stray objects whose drawing write lands in program code (seen with state `7B` writing to `A7F9`); `6E`'s writes before it crashes (flagged as desync, not reproduced); `38` at x = 96 (stale cell lookup) is modelled; 1681/1695 forced tests match and every remaining difference is announced in-game as a desync (untracked memory); and the code-`71` boxed-in case, which turned out to be stack-dependent on the original (irregular N/S flips, extra moves for other objects); the remake shows the desync notice there.

**G. Large MS-solution sets (Joshie 1325 levels, Jacques 986).** 2306 of 2311 outcomes reproduced on the same tick (doc 09 §9). These runs found three rules, now in doc 03: only slot 0 collects a counted chip normally (any other object arriving on one triggers a different path, §3.8); fire and water treat slot 0 as Chip whatever its type (§3.10–3.11); and the cartridge has no chips-required field (doc 02 §4). The five remaining differences are display effects.

**I. Every crash traced.** All 258 crashes/hangs in the real replays now have a known cause, reproduced on the same tick (doc 09 §13): 26 buttons without a target (hang at level start), 231 objects at or past the map edge (seven of them crash during the crossing tick itself), and one teleport writing over a dying object's map reference (CCLP5 11).

**J. Replay start fixed.** Tile World runs a level from tick 0 even when a solution's first move comes later; the cartridge waits for the first input. 74 replays started late until the tick-0 start (an A press) was added to both the original's harness and the remake; 63 outcomes changed, 5 of them to wins (CC1 100, 102; CCLP1 17, 48; CCLP5 85). All tables (doc 09 §6–§9) were updated, and the remake matches every one.

**K. Initial random-force-floor direction.** Lynx-ruleset solution files record the direction their random force floors start in (the slide value); the replays now set the cartridge's counter from it (doc 09 §6). 3 outcomes changed, 2 of them to wins (CC1 54, CCLP1 16). The remake applies the same rule in its test runner and replay mode and matches all tables.

**C. Block-slap tests.** Five dedicated test rooms (block plus Chip, with slap, walking slap, 180° slap, ordinary push, and a walk-away-then-slap sequence) all matched tick-for-tick and confirmed the behaviour described in doc 04 §3.1.

One test-room failure was a harness error rather than a doc error: the test room put a block in slot 0, which breaks the "slot 0 is Chip" invariant (doc 02 §2.2).

## 3. Original quirks (decide per quirk: *faithful* vs *fixed* mode)

A reimplementation should reproduce these by default (they affect level solutions and timing) and may offer a "fixed" option.

1. **Block launched by Chip's decision probe** (doc 04 §3): a block can start moving even if Chip ends up choosing another held direction.
2. **Monster that kills Chip vanishes** — it becomes a Chip-death effect too (doc 04 §3).
3. **Tank reversal only affects idle tanks** in the tick after the press (doc 04 §9).
4. **"Random" force floor is a global cycle** N→E→S→W, persisting across levels from power-on (doc 03 §3.4).
5. **Global tick counter** (Teeth timing, Blob randomness) persists across levels from power-on; the **RNG is reset to 0 every attempt** (doc 04 §1).
6. **Clock sub-second counter is not reset** between attempts (doc 05 §4).
7. **Teleport onto an occupied teleport** detaches the occupant from the map (doc 04 §6) — rare.
8. **No bounds checks at map edges** — off-map moves read/write the RAM just outside the map (row-31 link bytes above, object state bytes below) and coordinates wrap (doc 04 §4.2). Faithful mode reproduces this; the behaviour of what such writes produce (odd tile codes, stray types, corrupted links) was measured and is tabulated in doc 04 §4.4. Not described: what *drawing* an odd code does (position- and timing-dependent; doc 04 §4.4, last paragraph).
9. **Buttons with no target** hang the original at level start (verified, doc 02 §5) — treat as unlinked if such levels should be playable.
10. **Chips collected only on arrival**; monsters starting on chip tiles never collect them (doc 03 §3.8).
11. **Probe-mode door handling**: Chip's direction choice treats doors as blocked even when he holds the key; the real move then opens the door (doc 05 §2.2).
12. Level 12 really requires 652 chips (it is filled with counted chip tiles).

## 4. Open items (for a follow-up analysis pass)

**Audio (doc 08)**
- Music (only needed to recreate the cartridge's own music, not for gameplay): the precise early note-off rule (besides the release record, the driver may cut a still-sounding note when its volume has decayed past a per-voice threshold); initial voice-block contents come from the program image (MAIN `$80BE`, 4 × 0x36 bytes) and should be extracted rather than re-typed.
- Effects 04, 0A, 0D: confirmed never requested in 394 replays (CC1, CCLP1, CCLP5; doc 08 §3).
- Sound-effect triggers verified tick for tick against the original on those replays, including the bump latch (doc 08 §3).

**Presentation (docs 06/07)**
- Title/attract choreography (falling pieces, credits scroller) and the ending's exact sequence/timing are only outlined. The ending is believed to repeat after A/B because the same end-marker slot is reloaded (inferred from flow).
- HUD pixel positions are approximate (±2 px); measure from screenshots of the original if pixel-exactness matters.
- Story page 17 is **unused** (checked in emulation): its schedule entry is 0, so the level-advance check never selects it, and neither the ending sequence nor a normal level finish reads its pointer. Forced on screen (schedule entry set to 1), it appears after the score tally like any story page: a short congratulation for finishing the challenge — apparently an ending text the final game replaced with the graphical ending.

**Input naming** — "Option 1" / "Option 2" follow the usual Lynx register convention (joystick register bit 3 = Option 1, bit 2 = Option 2; Pause is a separate switch). The raw direction bits are orientation-dependent on real hardware and irrelevant for a PC port: map keys straight to N/E/S/W.

**Rules (docs 03–05)** — verified by the replays in §2. Rare paths now exercised: map-edge moves (doc 09 §11, §13), a clone machine with Chip on it (doc 09 §12), a dying object detached from the map by a teleport (doc 09 §13, CCLP5 11). Cloners filling the object table: tested (doc 09 §16) — the count stops at 128, the last press releases the waiting copy and leaves the machine empty, no crash.

**Desync notice coverage** — every remaining remake-vs-original difference in the synthetic tests raises the in-game desync notice. The notice has three kinds: unmapped memory, behaviour not yet mapped, and *likely crash*. The last covers an object in state `7B` drawn on screen; odd tile `47` can create one by writing Chip's screen position into object state bytes. Drawing it writes into program code. In 1450 code-`47` runs this happened 5 times. The original crashed in 4, 1–22 ticks later and always during a screen scroll, though one earlier scroll passed safely. It did not crash in the fifth, where the camera never scrolled. Because the crash is neither certain nor predictable to the tick, the remake does not crash there: it shows the likely-crash notice and plays on.

## 5. Recommended next steps for the clean team

1. Build the extractor from docs 01, 02, 07 and validate with doc 09.
2. Build the engine from docs 03–05 with a deterministic tick API (`tick(input) → state`), plus a state-hash per tick for regression testing.
3. Build the SDL2 front-end (doc 06) and a simple audio layer (doc 08 §6 option 2), then upgrade to the faithful synthesizer.
4. Ask the dirty team for targeted lock-step traces (input sequence → per-tick state hashes from the original) whenever behaviour is unclear; the dirty team can produce them without disclosing code.
