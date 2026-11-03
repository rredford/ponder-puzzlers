# 05 — Player Control, Game Loop, Timing & Scoring

## 1. Frame pacing

- The Lynx display runs at ≈ **59.9 Hz** (one frame ≈ 16.70 ms).
- The game loop waits for **3 frames per iteration** ⇒ one **tick ≈ 50.1 ms (≈ 19.97 ticks/s)**. Logic, rendering, HUD and scrolling all update once per tick.
- A reimplementation should run the simulation at exactly 1 tick per 3 frames of a 59.9 Hz clock (or simply 20 Hz) and may render at any rate (interpolation optional, but the original shows positions only at tick resolution).

## 2. Chip's input handler (decision phase, slot 0)

Inputs are the four directions currently held. The handler keeps two pieces of memory across ticks: `prev_dirs` (directions held at the previous poll) and `preferred` (a set of directions), plus `last_choice` (Chip's state byte from his last voluntary decision).

```
chip_decide():
  if state[0] == 0: return
  if under[0] == TELEPORT: return                    # no control on teleports
  if ICE(under[0]) and not boots.skates: return       # no control while sliding on ice
  if not aligned(0): return
  if moving(last_choice) and moving(state[0]):        # see §2.1
      last_choice = 0; return
  held = directions held now
  pushing_pose = false
  if held is empty: clear bump latch; return
  newly = held − prev_dirs ; prev_dirs = held
  if newly non-empty: preferred = newly
  d = start direction for `preferred` (table below)
  pending = held
  loop:
      if d in pending:
          remove d from pending
          state[0] = CHIP, moving, direction d
          if test_move(0) == PASSABLE: last_choice = state[0]; return
          if Chip died: return
          pushing_pose = true
      if pending empty: break
      d = (d + 1) mod 4                               # clockwise
  state[0] = CHIP, moving, direction d                # last direction tried
  last_choice = state[0]
```

So: the most recently pressed direction is tried first; if it is blocked, the other held directions are tried **clockwise** from it; if all are blocked Chip faces the last one tried and his real move fails (bump sound, doc 04 §4.1).

Start direction when several directions become pressed at the same poll:

| Newly pressed | Start | Newly pressed | Start |
|---|---|---|---|
| N | N | S + N | N |
| E | E | S + E | E |
| S | S | S + W | W |
| W | W | N + E + W | N |
| N + E | E | S + E + W | S |
| N + W | W | S + N + W | W |
| E + W | E | S + N + E | E |
| | | all four | E |

`pushing_pose` selects Chip's pushing/straining animation (doc 06 §5).

### 2.1 Forced moves (force floors, traps)
A force floor's ARRIVE handler sets Chip's moving flag (forced). On the next decision, if his *previous* decision was also a voluntary move, the input is skipped once (`last_choice` cleared) and the forced move happens. On the following arrival Chip may override the force with any held direction (except against the flow, which the leave mask forbids). Net effect: **holding a direction on a force-floor run lets Chip act on every other tile.** The same rule lets a trapped Chip re-aim while waiting.

### 2.2 Probe semantics for Chip
During this decision `probe = 1`: doors and hidden/blue walls count as blocked (they are opened/revealed by the real move test in the movement phase); pushing a block during the probe already launches the block (doc 04 §3 quirk); a monster in the tested cell kills Chip immediately.

## 3. Per-iteration game loop (one tick)

1. **System buttons** (edge-triggered on the combination of Pause, Option 1, Option 2): see §6.
2. If the level is *finished* and its score has not been computed: compute score (§5). Otherwise, if **Option 1** is held: restart the current level immediately.
3. If not paused and Chip is *waiting for first input* and any direction or A/B is pressed: `attempts += 1` (capped at 127) and leave the waiting state.
4. Update tile animations (doc 06 §5) — also while paused/waiting — and, if chips-left is 0, open the socket (doc 03 §3.7).
5. If the game is **running** (not waiting, not paused, not dead, not finished): `tick` processing (doc 04 §2) and the clock (§4).
6. Render the frame (map, objects, HUD, overlays) and wait for the 3-frame boundary.
7. If Chip's slot is empty (death effect finished): count down a 4-tick grace period, then enter the *dead* state.
8. Update the time display; update `tank_reverse` (doc 04 §9); manage looping sounds (doc 08).
9. If a level transition was requested by the end-of-level screen: start the next/same level.

Creatures and the clock do not move until Chip's first input of an attempt.

## 4. Clock

- `time_left` is the level's time limit (seconds). If it is 0 the level is untimed and nothing below happens.
- A sub-second counter counts running ticks; every **20 running ticks** `time_left −= 1`. The sub-second counter is *not* reset between attempts, so the first second of an attempt may be shorter.
- When `time_left` reaches 0: Chip becomes a Chip-death effect, `death_reason = time-out`.
- The HUD shows 3 digits; untimed levels (and a timed-out clock) display `---`.
- A second counter (200 running ticks ≈ 10 s, re-armed at each attempt start) decrements the *skip counter* (§7) once per attempt that lasts that long.

## 5. Scoring (computed once when Chip reaches the exit)

- **Time bonus** = `time_left × 10`.
- **Level bonus** = `level_number × F`, where `level_number` is 1-based and `F` depends on the attempt count for this level: 1st attempt → 500, 2nd → 400, 3rd → 300, 4th → 200, 5th or later → 100. **Minimum 500.**
- **Level score** = time bonus + level bonus. **Total score** += level score (24-bit; shown with 7 digits; starts at 0 when a game is started from the title).
- Attempts are counted at each attempt's first input; the counter resets when a new level is reached (completion, skip or password).

Completion praise line, chosen by `attempts − 1`: 0 → "first try" message; 1–2 and 3–4 → "go bit buster"-style message; 5–9 → "finished, good work"; ≥ 10 → "at last, you did it" (exact strings are in the ROM, doc 06 §7).

## 6. System buttons

Lynx buttons: D-pad, **A**, **B**, **Option 1**, **Option 2**, **Pause**.

| Input | Effect |
|---|---|
| D-pad | Move Chip; menu cursor |
| A or B | Start / confirm / dismiss screens. During play only counts as "first input" |
| Pause | Toggle pause (shows "PAUSED", level title and code). Music is silenced while paused |
| Option 1 (during play) | Restart the current level |
| Option 2 | Toggle music on/off (when not paused) |
| Pause + Option 2 | Toggle 180° screen flip (left-handed play) |
| Pause + Option 1 | Abort to the title sequence |

System combinations act when the combination changes (any newly pressed member), evaluating the whole combination held at that moment.

## 7. End of an attempt

- **Finished** (Chip on the exit): at the end of the tick in which the exit is reached, Chip's object is removed (slot cleared, exit tile restored in the map); overlay shows the praise line and the four score lines; A/B → next level (level index +1). When the new level index is 10, 20, …, 140 (i.e. starting levels 11, 21, …, 141) a story page is shown first (doc 06 §3). Attempts reset; skip counter reset to 10.
- **Dead** (killed or out of time): overlay shows the death message ("oops" vs "out of time"); A/B → restart the same level.
- **Skip offer:** at the start of an attempt, if the level number is ≤ 139 and the *skip counter* has reached 0 (it starts at 10 and drops once per attempt lasting ≥ ~10 s), a dialog asks whether to skip the level (YES / NO, default NO, left/right to choose, A/B to confirm). YES advances one level and resets attempts. Either way the skip counter returns to 10.
- **End of game:** loading slot 145 or 150 (marker files) runs the ending sequence instead of a level (doc 06 §8).
