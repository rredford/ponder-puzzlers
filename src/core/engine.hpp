// Deterministic game simulation (spec docs 03, 04, 05).
#pragma once
#include <array>
#include <cstdint>
#include <vector>
#include "level.hpp"

namespace cc {

enum Dir : uint8_t { N = 0, E = 1, S = 2, W = 3 };
enum DirBit : uint8_t { kN = 1, kE = 2, kS = 4, kW = 8 };   // input bitmask uses these
inline uint8_t dirBit(int d) { return static_cast<uint8_t>(1u << d); }

enum ObjType : uint8_t {
    T_NONE = 0, T_CHIP = 1, T_BUG = 2, T_PARAMECIUM = 3, T_FIREBALL = 4, T_GLIDER = 5,
    T_BALL = 6, T_BLOCK = 7, T_TANK = 8, T_WALKER = 9, T_BLOB = 10, T_TEETH = 11
};

// Tile codes (doc 03 §2)
namespace tile {
enum : uint8_t {
    Floor = 0x00, Wall = 0x01, Ice = 0x02, Dirt = 0x03, FakeBlueWall = 0x04,
    ForceN = 0x05, ForceE = 0x06, ForceS = 0x07, ForceW = 0x08, ForceRandom = 0x09,
    IceNW = 0x0A, IceNE = 0x0B, IceSE = 0x0C, IceSW = 0x0D, Teleport = 0x0E,
    Skates = 0x0F, FireBoots = 0x10, SuctionBoots = 0x11, Flippers = 0x12,
    Fire = 0x13, Water = 0x14, Thief = 0x15, PopupWall = 0x16, ToggleOpen = 0x17, ToggleClosed = 0x18,
    GreenButton = 0x19, DoorRed = 0x1A, DoorBlue = 0x1B, DoorYellow = 0x1C, DoorGreen = 0x1D,
    KeyRed = 0x1E, KeyBlue = 0x1F, KeyYellow = 0x20, KeyGreen = 0x21, BlueButton = 0x22,
    Chip = 0x23, Socket = 0x24, Exit = 0x25, HiddenWall = 0x26, InvisibleWall = 0x27, Gravel = 0x28,
    ThinE = 0x29, ThinS = 0x2A, ThinSE = 0x2B, Bomb = 0x2C, Trap = 0x2D, BrownButton = 0x2E,
    Cloner = 0x2F, RedButton = 0x30, ChipUncounted = 0x31, RealBlueWall = 0x32, Hint = 0x33,
    // extended mode only (not on the cartridge): thin walls on the north / west edge
    ThinN = 0x34, ThinW = 0x35,
    Count = 0x36
};
}

// Sound effect ids (doc 08 §3)
enum Sfx : uint8_t {
    SFX_PICKUP = 0x00, SFX_POPUP = 0x01, SFX_THIEF = 0x02, SFX_EXIT = 0x03, SFX_DOOR = 0x05,
    SFX_ICE_LOOP = 0x06, SFX_BOOTS = 0x07, SFX_BUMP = 0x08, SFX_DEATH = 0x09, SFX_CLEAR = 0x0B,
    SFX_SPLASH = 0x0C, SFX_FORCE_LOOP = 0x0E, SFX_PUSH = 0x0F, SFX_FIREWALK = 0x10, SFX_SWIM = 0x11
};

// Values that persist across attempts and levels (doc 04 §1, doc 05 §2/§4).
struct Globals {
    uint8_t tick = 0;          // global tick counter
    uint8_t randomForce = 0;   // R, 0..3
    int subSecond = 0;         // running ticks since last clock decrement
    uint8_t prevDirs = 0;      // input memory
    uint8_t preferred = 0;
    uint8_t lastChoice = 0;
    // Bump-sound latch (set by a bump sound, cleared by a tick without input), never reset between levels. The title
    // screen leaves it set, so a blocked first move of the first level is silent (measured; doc 08 §3).
    bool bumpLatch = true;
    // The cartridge's button/teleport link table (doc 02 §5, doc 04 §4.2). The original never clears it, so
    // entries of cells that are not link sources keep earlier levels' values; the high half of row 31 is the
    // RAM the map reaches off its top edge.
    std::array<uint8_t, 1024> linkLo{};
    std::array<uint8_t, 1024> linkHi{};
};

struct Input {
    uint8_t dirs = 0;   // DirBit mask
    bool ab = false;    // A or B pressed (counts as first input)
};

// A map cell holds a tile code, or an object reference (kObj | slot).
using Cell = uint16_t;
constexpr Cell kObj = 0x8000;
inline bool isObj(Cell v) { return (v & kObj) != 0; }
inline int objOf(Cell v) { return v & 0x7FFF; }
inline Cell objCell(int i) { return static_cast<Cell>(kObj | i); }
constexpr int kMaxExtendedSlots = 2 * kMapCells;   // as Tile World's Lynx mode

// Crash: the original program would run off its tables here (undefined behaviour - doc 04 §4.2).
enum class DeathReason : uint8_t { None, Killed, TimeOut, Crash };


class Game {
public:
    Game(const LevelData& lvl, Globals& g);

    void tick(const Input& in);

    // ---- state queries
    bool waiting() const { return waiting_; }
    bool finished() const { return finished_; }
    bool dead() const { return dead_; }
    bool running() const { return !waiting_ && !finished_ && !dead_; }
    DeathReason deathReason() const { return death_; }
    // Strict mode: a stale cell lookup (code 38 drawn at x = 96, doc 04 §4.4) read cartridge RAM this remake does
    // not track, so from here the attempt may no longer match the original.
    bool outOfSync() const { return outOfSync_; }
    uint8_t soundGlitch() const { return soundGlitch_; }   // 0, or the odd tile (67 / 6C) whose drawing altered sound data
    // 1: the glitch reached memory the remake does not track; 2: it reached behaviour that is known but not mapped
    int desyncReason() const { return syncReason_; }
    // which glitch: 1 stale lookup read scratch memory, 2 code 6E animation writes, 3 teleport with a stale lookup,
    // 4 Chip boxed in on code 71, 5 button link overwritten by drawing, 6 row table shifted while scrolling,
    // 7 object in state 7B drawing into code
    int desyncDetail() const { return syncDetail_; }
    void debugMarkOutOfSync(int why = 1, int what = 0) { flagDesync(why, what); }
    void debugMarkSoundGlitch(uint8_t code) { soundGlitch_ = code; }   // headless UI screenshot only   // headless UI screenshot only
    int timeLeft() const { return time_; }
    int timeLimit() const { return timeLimit_; }
    int chipsLeft() const { return chips_; }
    int key(int k) const { return keys_[k]; }
    bool skates() const { return skates_; }
    bool suction() const { return suction_; }
    bool fireBoots() const { return fire_; }
    bool flippers() const { return flippers_; }
    bool togglesSwapped() const { return swapped_; }
    bool pushingPose() const { return pushing_; }
    const LevelData& level() const { return *lvl_; }

    int slots() const { return nSlots_; }
    Cell cell(int c) const { return map_[c]; }
    uint8_t objState(int i) const { return state_[i]; }
    int objX(int i) const { return x_[i]; }     // 1/8-tile units
    int objY(int i) const { return y_[i]; }
    uint8_t objUnder(int i) const { return static_cast<uint8_t>(under_[i]); }
    int objUnderRaw(int i) const { return isObj(under_[i]) ? 0x80 | (objOf(under_[i]) & 0x7F) : under_[i]; }

    // Sound effects triggered during the last tick (ids, doc 08 §3).
    const std::vector<uint8_t>& sounds() const { return sounds_; }
    // Looping sound wanted this tick: 0 none, SFX_ICE_LOOP or SFX_FORCE_LOOP.
    uint8_t loopSound() const;
    bool chipOnHint() const;
    bool displayWouldHang() const;     // strict mode: the original's map drawing would loop forever
    void drawPass();                   // strict mode: what drawing odd tile codes writes (doc 04 §4.4)
    // Test hook: write a byte into the modelled RAM (see peek/poke in engine.cpp), as an experiment would.
    void debugPoke(int addr, uint8_t v) { poke(addr, v); }
    void debugNoDraw() { noDraw_ = true; }   // test switch: leave out the drawing effects (for comparison)
    uint8_t debugPeek(int addr) const { return peek(addr); }

private:
    struct TileProps { uint8_t entry, leave, flags; };
    enum { F_SPECIAL = 1, F_SLIDE = 2, F_ICE = 4 };
    enum Event { ARRIVE, STAY };

    // helpers
    // With code 38 drawn at x = 96 the original's cell lookup returns at once, leaving the last cell it or the
    // map drawing computed (doc 04 §4.4).
    // The cell of an object: high part from the row, low byte from the row table (0x2F53 + row, normally row * 32),
    // plus the column. Drawing a stray object in state F5 can overwrite table entries (doc 04 §4.4).
    int cellOf(int i) const {
        if (staleCells()) return curCell_;
        int r = (y_[i] / 8) & 31;
        return ((r >> 3) << 8) + rowLo_[r] + x_[i] / 8;
    }
    bool rowTableShifted() const { for (int r = 0; r < 32; ++r) if (rowLo_[r] != static_cast<uint8_t>(r * 32)) return true; return false; }
    bool aligned(int i) const { return (x_[i] & 7) == 0 && (y_[i] & 7) == 0; }
    int type(int i) const { return (state_[i] >> 2) & 15; }
    int dir(int i) const { return state_[i] & 3; }
    bool moving(int i) const { return state_[i] & 0x80; }
    bool dying(int i) const { return state_[i] & 0x40; }
    bool alive(int i) const { return state_[i] != 0 && !dying(i); }
    void setDir(int i, int d) { state_[i] = static_cast<uint8_t>((state_[i] & ~3) | (d & 3)); }
    void setMoving(int i) { state_[i] |= 0x80; }
    void stop(int i) { state_[i] &= 0x7F; }
    uint8_t classMask(int i) const;
    static constexpr int kOffMap = -100000;
    const TileProps& pr(Cell v) const { return props_[isObj(v) ? (0x80 | (objOf(v) & 0x7F)) : (v & 0xFF)]; }
    // An object reference standing in for a tile (only after off-map writes) uses the byte value 0x80|slot as a
    // tile code: its properties were measured (stray_tables.inc, kRefTiles).
    uint8_t entryOf(Cell v) const { return pr(v).entry; }
    uint8_t leaveOf(Cell v) const { return pr(v).leave; }
    uint8_t flagsOf(Cell v) const { return pr(v).flags; }
    void syncAlias(int code);
    int neighbour(int c, int d) const;
    Cell readCell(int c) const;
    void writeCell(int c, Cell v);
    uint8_t peek(int addr) const;          // the original's RAM as far as it is modelled (else: crash)
    void poke(int addr, uint8_t v);
    Cell byteToCellAt(int addr) const;
    void setAt(int addr, Cell v);
    int linkAddr(int c) const;
    void sfx(uint8_t id) { sounds_.push_back(id); }
    void sfxChip(int i, uint8_t id) { if (i == 0) sfx(id); }

    bool testMove(int i);
    bool specialBump(int i, Cell v, int t);
    bool pushBlock(int j);
    void killChipBy(int k);
    void advance(int i);
    void step(int i);
    void handler(int i, Event ev);
    void teleport(int i);
    void ai(int i);
    void chipDecide(uint8_t held);
    void removeObject(int i);
    void doTick(uint8_t held);

    const LevelData* lvl_;
    Globals& g_;
    TileProps props_[256];
    int nSlots_ = kSlots;
    int redirectDepth_ = 0;
    bool abortMoves_ = false;
    int drawCrashIn_ = -1;    // ticks until the damage from drawing a junk Chip crashes the original
    // Program code damaged by drawing odd tile codes (doc 04 §4.4): 61 (code run every tick), 6E (last x value
    // written; by value, code run every tick or every 6th tick), 38 (Chip's move code).
    bool hit61_ = false;
    int v38_ = -1;            // last x value drawing 38 wrote; 0x60 (an early return) does not crash
    bool moveCodeBroken() const { return v38_ >= 0 && v38_ != 0x60; }
    bool staleCells() const { return v38_ == 0x60; }
    int curCell_ = 0;         // the cell lookup's last result (Chip's cell at level start; after drawing: above the window)
    int v6E_ = -1;
    uint32_t frames_ = 0;
    uint8_t rowLo_[32] = {};   // row table of the cell lookup (initialised to row * 32 in the constructor)
    bool noDraw_ = false;
    std::array<bool, 1024> linkDrawn_{};   // link entries overwritten by drawing this level
    void checkDrawnLink(int c, int A) const;     // tick() calls since the level started (the 6-tick animation cycle)
    std::array<Cell, kMapCells> map_;
    std::array<int16_t, kMapCells> link_;
    std::vector<uint8_t> state_;
    std::vector<Cell> under_;
    std::vector<int> x_, y_;
    uint8_t keys_[4] = {0, 0, 0, 0};    // 8-bit counts: the 256th key wraps to 0 (doc 04 §1)
    bool skates_ = false, suction_ = false, fire_ = false, flippers_ = false;
    bool swapped_ = false;
    int chips_ = 0, time_ = 0, timeLimit_ = 0;
    bool waiting_ = true, finished_ = false, dead_ = false;
    mutable bool crashed_ = false;
    uint8_t soundGlitch_ = 0;
    bool fakeNW_ = false;      // codes 34/35 act as north/west thin walls (extended mode, or test switch CC_FAKE_NW)
    mutable bool outOfSync_ = false;
    mutable int syncReason_ = 0;
    mutable int syncDetail_ = 0;
    void flagDesync(int why, int what = 0) const { if (!outOfSync_ || (why == 3 && syncReason_ != 3)) { outOfSync_ = true; syncReason_ = why; syncDetail_ = what; } }
    DeathReason death_ = DeathReason::None;
    int grace_ = 3;
    uint8_t tankReverse_ = 0;
    uint8_t probe_ = 0;
    bool pushing_ = false;
    Rng rng_;
    std::vector<uint8_t> sounds_;
};

} // namespace cc
