# 03 — Tile Catalogue & Tile Rules

The map holds one tile code (`0x00–0x33`) per cell. Objects (Chip, monsters, blocks) are *not* tiles; they sit on top of a tile (doc 04).

## 1. Passability model

Each tile has three functional attributes:

- **Entry mask** (8 bits) — who/what may move *into* the tile.
- **Leave mask** (4 bits) — directions in which nothing may move *out of* the tile.
- **Flags**: `SPECIAL` (bump handling for doors & hidden walls), `SLIDE` (movement on it is forced and fast), `ICE` (ice-type sliding: bounce when blocked; requires skates for control).

In memory the 52 entry masks are directly followed by the 52 leave/flag bytes (bit 7 `SPECIAL`, bit 6 `SLIDE`, bit 5 `ICE`, bits 3–0 leave mask). Only codes `00–33` occur in levels; the larger codes reachable off the map edge are covered in doc 04 §4.2.

Every mover has a **class mask** = class bits | direction bit:

| Mover | Class bits |
|---|---|
| Chip | `0x00` |
| Block | `0x10` |
| Fireball | `0x50` |
| Any other monster | `0x70` |

Direction bits (of the direction of travel): `N = 0x01`, `E = 0x02`, `S = 0x04`, `W = 0x08`.

- **Entry is blocked** if `entry_mask & class_mask ≠ 0`.
- **Leaving is blocked** if `leave_mask & direction_bit ≠ 0` (for the tile the mover currently stands on).

So entry-mask bits mean: `0x0F` = solid from the given approach directions (for everybody); `0x10` = blocks blocks and all monsters (Chip-only tile); `0x20` = blocks monsters except Fireball (blocks and Chip pass); `0x40` = blocks all monsters (blocks and Chip pass).

A direction bit in an entry mask blocks movers *travelling in that direction*: e.g. entry mask `0x08` (W) means "cannot be entered while moving west", i.e. there is a wall on the tile's **east** edge.

## 2. Catalogue

Columns: **Entry** / **Leave** masks, **Flags** (S = SPECIAL, F = SLIDE, I = ICE), **C/B/Fb/M** = can Chip / Block / Fireball / other Monsters enter (ignoring direction-specific edges). Behaviour column summarises the tile handler (§3); "→ floor" means the tile is replaced by Floor `0x00`.

| Code | Name | Looks like | Entry | Leave | Flags | C/B/Fb/M | Behaviour |
|---|---|---|---|---|---|---|---|
| 00 | Floor | floor | 00 | – | | ✓✓✓✓ | — |
| 01 | Wall | wall | 0F | – | | ✗✗✗✗ | — |
| 02 | Ice | ice | 00 | – | F I | ✓✓✓✓ | Slide; Chip with skates walks normally |
| 03 | Dirt | dirt | 10 | – | | ✓✗✗✗ | → floor when stood on (sfx 0B for Chip) |
| 04 | Blue wall (fake) | blue wall | 10 | – | | ✓✗✗✗ | → floor when stood on (sfx 0B for Chip) |
| 05 | Force floor N | arrows N | 00 | S | F | ✓✓✓✓ | Force north |
| 06 | Force floor E | arrows E | 00 | W | F | ✓✓✓✓ | Force east |
| 07 | Force floor S | arrows S | 00 | N | F | ✓✓✓✓ | Force south |
| 08 | Force floor W | arrows W | 00 | E | F | ✓✓✓✓ | Force west |
| 09 | Force floor, "random" | cycles through the four force-floor looks | 00 | – | F | ✓✓✓✓ | Force in cyclic direction (§3.4) |
| 0A | Ice corner, walls N+W | ice corner | 06 | N W | F I | edges | Deflect (§3.3) |
| 0B | Ice corner, walls N+E | ice corner | 0C | N E | F I | edges | Deflect |
| 0C | Ice corner, walls S+E | ice corner | 09 | E S | F I | edges | Deflect |
| 0D | Ice corner, walls S+W | ice corner | 03 | S W | F I | edges | Deflect |
| 0E | Teleport | teleport | 00 | – | | ✓✓✓✓ | Teleport (doc 04 §6) |
| 0F | Ice skates | skates | 10 | – | | ✓✗✗✗ | Chip: get skates, → floor (sfx 00) |
| 10 | Fire boots | flame shield | 10 | – | | ✓✗✗✗ | Chip: get fire boots, → floor (sfx 00) |
| 11 | Suction boots | magnet | 10 | – | | ✓✗✗✗ | Chip: get suction boots, → floor, disable force-floor leave masks (sfx 00) |
| 12 | Flippers | water shield | 10 | – | | ✓✗✗✗ | Chip: get flippers, → floor (sfx 00) |
| 13 | Fire | fire | 20 | – | | ✓✓✓✗ | Kills Chip without fire boots; harmless to blocks & fireballs |
| 14 | Water | water | 00 | – | | ✓✓✓✓ | Drowns Chip without flippers & all monsters except Glider; block → dirt |
| 15 | Thief | thief | 10 | – | | ✓✗✗✗ | Chip: lose all boots (sfx 02) |
| 16 | Recessed (pop-up) wall | dotted floor | 10 | – | | ✓✗✗✗ | Chip: becomes wall once Chip steps off (sfx 01) |
| 17 | Toggle wall, open | dashed outline | 00 ⇄ 0F | – | | ✓✓✓✓ | Swaps with `18` on green button (§3.6) |
| 18 | Toggle wall, closed | dashed wall | 0F ⇄ 00 | – | | ✗✗✗✗ | Swaps with `17` |
| 19 | Green button | button | 00 | – | | ✓✓✓✓ | Toggle walls (sfx 00) |
| 1A | Door, red | door | 0F | – | S | key | Needs red key (consumed) |
| 1B | Door, blue | door | 0F | – | S | key | Needs blue key (consumed) |
| 1C | Door, yellow | door | 0F | – | S | key | Needs yellow key (consumed) |
| 1D | Door, green | door | 0F | – | S | key | Needs green key (**not** consumed) |
| 1E | Key, red | key | 00 | – | | ✓✓✓✓ | Chip: +1 red key, → floor (sfx 00). Others walk over it |
| 1F | Key, blue | key | 00 | – | | ✓✓✓✓ | Chip: +1 blue key, → floor. Others walk over it |
| 20 | Key, yellow | key | 10 | – | | ✓✗✗✗ | Chip: +1 yellow key, → floor |
| 21 | Key, green | key | 10 | – | | ✓✗✗✗ | Chip: +1 green key, → floor |
| 22 | Blue button | button | 00 | – | | ✓✓✓✓ | Tanks reverse (sfx 00) |
| 23 | Computer chip | chip | 10 | – | | ✓✗✗✗ | Chip: chips-left −1 (if >0), → floor (sfx 00). **Counted** in chips-required |
| 24 | Socket | socket | 1F → 10 | – | | ✗ / ✓ | Blocks Chip until chips-left = 0, then Chip-only; → floor (sfx 05 + 0B) |
| 25 | Exit | exit | 10 | – | | ✓✗✗✗ | Chip: level finished (sfx 03) |
| 26 | Hidden wall | **floor** | 0F | – | S | ✗✗✗✗ | Becomes Wall `01` when Chip bumps it |
| 27 | Invisible wall | **floor** | 0F | – | S | ✗✗✗✗ | Never changes |
| 28 | Gravel | gravel | 40 | – | | ✓✓✗✗ | — |
| 29 | Thin wall, east edge | thin wall | 08 | E | | edges | — |
| 2A | Thin wall, south edge | thin wall | 01 | S | | edges | — |
| 2B | Thin wall, south+east edges | thin wall | 09 | E S | | edges | — |
| 2C | Bomb | bomb | 00 | – | | ✓✓✓✓ | Anything entering explodes; → floor (sfx 09) |
| 2D | Trap | trap | 00 | all | | ✓✓✓✓ | Holds anything until released by its brown button |
| 2E | Brown button | button | 00 | – | | ✓✓✓✓ | Releases linked trap (sfx 00) |
| 2F | Clone machine | cloner | 0F | all | | ✗✗✗✗ | Holds a template object (doc 04 §7) |
| 30 | Red button | button | 00 | – | | ✓✓✓✓ | Clone from linked cloner |
| 31 | Computer chip (uncounted) | chip | 10 | – | | ✓✗✗✗ | As `23` but not counted in chips-required |
| 32 | Blue wall (real) | blue wall (same as `04`) | 0F | – | S | ✗✗✗✗ | Becomes Wall `01` when Chip bumps it |
| 33 | Hint | "?" | 10 | – | | ✓✗✗✗ | Shows level hint while Chip stands on it |

Notes:
- Tiles `26`/`27` are drawn with the floor graphic; `04`/`32` share the blue-wall graphic; `23`/`31` share the chip graphic.
- Only thin walls on east/south edges exist in this version (no north/west thin walls).
- Hex codes not listed (`0x34–0x7F`) never occur.

## 3. Tile handlers (behaviour on arrival / while standing)

A tile's handler runs for the mover standing on it in two situations (precise timing in doc 04 §4):

- **ARRIVE** — the mover has just become tile-aligned after moving onto this tile (also used for an "ice bounce", doc 04 §4).
- **STAY** — the mover is on this tile and is not moving, or its attempted move this tick failed.

Unless stated otherwise a handler ends by **stopping** the mover (clearing its moving flag). "(Chip)" means the sound is only played when the mover is Chip; "(any)" means it is played whoever triggers it.

### 3.1 Inert tiles
Floor, wall, toggle walls, gravel, thin walls, hidden/invisible/blue walls, hint: stop the mover.

### 3.2 Ice `02`
- Chip **with skates**: on ARRIVE play sfx 07 (Chip); stop (Chip controls normally).
- Everyone else (including Chip without skates): **keep moving** (moving flag stays set ⇒ continues sliding in the same direction).

### 3.3 Ice corners `0A–0D`
Same skates rule as ice (Chip with skates: sfx 07 on ARRIVE, stop, no deflection). Otherwise the mover's direction is replaced using this table, the mover keeps moving, and sfx 0C is played (Chip):

| Tile | from N | from E | from S | from W |
|---|---|---|---|---|
| 0A (walls N+W) | E | E | S | S |
| 0B (walls N+E) | W | S | S | W |
| 0C (walls S+E) | N | N | W | W |
| 0D (walls S+W) | N | E | E | N |

("from X" = the mover's direction when the handler runs.)

**Standing still on a corner (STAY).** An object that is not moving on a corner — in practice one that starts the level there — only has its direction replaced by the table; it is **not** set moving and no sound plays. A block keeps standing; Chip, who cannot steer while standing on ice, stays put. Monsters choose a new move each tick and leave normally. *(Verified: 1280 lock-step runs, doc 09 §17.)*

### 3.4 Force floors `05–09`
- Chip **with suction boots**: on ARRIVE play sfx 07 (Chip); stop (normal control).
- Otherwise: set direction to the floor's direction (05 N, 06 E, 07 S, 08 W) and **set the moving flag** (forced move).
- `09` ("random"): a **global** counter `R` (0–3, never reset — persists across levels and attempts from power-on, starting at 0) is incremented (mod 4) each time the handler runs; the forced direction is the new `R` (0 = N …). So it actually cycles N→E→S→W→N for successive uses.
- Leave masks of force floors prevent walking *against* the flow (e.g. on a north floor you cannot step south). **Picking up suction boots clears the leave masks of tiles 05–08**; the thief (or a new level) restores them.

### 3.5 Teleport `0E`
On ARRIVE: sfx 03 (Chip), then the teleport procedure of doc 04 §6.

### 3.6 Buttons and toggles
- **Green button `19`** (ARRIVE only, any mover): swap the meaning of `17` and `18` (their entry masks *and* graphics swap globally; the map codes themselves don't change). sfx 00 (any).
- **Blue button `22`** (ARRIVE only, any mover): toggle the tank-reverse request (doc 04 §8). sfx 00 (any).
- **Brown button `2E`**: on ARRIVE sfx 00 (any). On ARRIVE *and* STAY: if the linked trap cell holds an object, release it (doc 04 §7). So a trap is open for as long as something stands on its button.
- **Red button `30`** (ARRIVE only): clone from the linked cloner (doc 04 §7).

### 3.7 Doors & socket
The socket's entry mask is `1F` (blocks everyone) while chips remain. At the **start of every loop iteration** (before the tick is processed, and also while paused/waiting) the game checks chips-left; if it is 0 the socket's entry mask becomes `10` (Chip only). So collecting the last chip in tick *t* opens the socket from tick *t + 1*.

Opening happens during the move test (doc 04 §3): a door is passable for Chip only if he holds a key of that colour; the key is consumed except for green. When an object arrives on (or stands on) a door or socket: sfx 05 then sfx 0B (Chip only), tile → floor, stop. The conversion applies to **any** object — only Chip can normally get there, but an object that starts the level on such a tile converts it on the first tick.

### 3.8 Pick-ups
Keys `1E–21` (+1 to that colour's count) and boots `0F–12` (set flag): Chip only, on ARRIVE or STAY; sfx 00, tile → floor. Other movers just stop — **except on a blue key `1F`: any other object (monster or block) arriving on or standing on it destroys it (tile → floor, no sound).** Red keys are not affected. *(A deliberate rule that none of the cartridge's own levels happens to use; found with CCLP1 level 84, where blocks start on blue keys.)*
Chips `23`/`31`: on ARRIVE only (STAY does nothing); decrement chips-left if non-zero, update HUD, sfx 00 (Chip), tile → floor. Monsters that start a level standing on a chip never collect it, and monsters and blocks cannot enter one.
*Only slot 0 collects a counted chip `23` this way (verified with imported levels).* Any other object that arrives on one — only a Chip-type object in another slot or a stray object (doc 04 §4.4) can — triggers a different path: chips-left is decremented, but the chip **stays** on the map (it can be counted again), the mover keeps its moving flag, **slot 0's moving flag is cleared** (Chip stops where he is, even between two cells), and the rest of that tick's movement phase is skipped (all lower slots, Chip included, do not move this tick; the clock still runs). The pickup's "tile → floor" also lands on slot 0: **the tile under slot 0 becomes floor** (written just before slot 0's state). This is invisible while Chip stands on floor; on ice, a force floor or any other tile it replaces that tile under him. The uncounted chip `31` has no such path.

### 3.9 Dirt `03`, fake blue wall `04`
Any object arriving on or standing on it (ARRIVE or STAY): tile → floor; sfx 0B (Chip only). As with doors, monsters can't enter these tiles, but one that *starts* on one (e.g. a Bug placed on a fake blue wall) clears it on the first tick.

### 3.10 Fire `13` (ARRIVE only)
*"Chip" in §3.10 and §3.11 means **slot 0**, whatever its type: a level without a player start puts a monster in slot 0, and it is then treated like Chip here (verified).*
- Slot 0 with fire boots: sfx 10. Slot 0 without: dies (even a fireball or block).
- Fireball or Block (other slots): nothing.
- Any other monster: dies — becomes an *explosion* effect (doc 04 §8), sfx 09 (slot 0); if slot 0, death reason = killed.

### 3.11 Water `14` (ARRIVE and STAY)
Slot 0 is tested first:
- Slot 0 with flippers: on ARRIVE sfx 11 (swim); stop. Slot 0 without flippers drowns, even a glider or a block (no dirt).
- Glider (other slots): nothing (stop).
- Block (other slots): sfx 0C; block becomes a *splash* effect; the tile under it becomes **Dirt `03`**.
- Any other monster: drown — *splash* effect, sfx 0C (any); if slot 0, death reason = killed.

### 3.12 Thief `15` (ARRIVE, Chip)
Remove all four boots (and restore force-floor leave masks). sfx 02.

### 3.13 Recessed wall `16` (Chip)
Immediately changes the tile under Chip to Wall `01` (so the wall appears when he leaves). sfx 01.

### 3.14 Exit `25` (Chip)
If not already finished: set *level finished*, sfx 03.

### 3.15 Bomb `2C` (ARRIVE, any mover)
sfx 09 (any); the mover becomes an *explosion* effect; tile under it → floor; if Chip, death reason = killed.

### 3.16 Trap `2D`
On ARRIVE: sfx 08 (any). The handler does **not** stop the mover: it keeps its moving flag and direction, and simply fails to leave (leave mask = all) until released.

### 3.17 Hidden wall `26`, blue wall `32`
When Chip's real (non-probe) move test bumps into one, it is replaced by Wall `01` (now visible). The move fails.
