#include "engine.hpp"
#include "rom.hpp"
#include <algorithm>
#include <cstdlib>
#include <cstdio>

namespace cc {
using namespace tile;

static const int kDX[4] = {0, 1, 0, -1};
static const int kDY[4] = {-1, 0, 1, 0};
// Ice-corner deflection (doc 03 §3.3), indexed [corner-IceNW][dir]
static const uint8_t kCorner[4][4] = {
    {E, E, S, S}, {W, S, S, W}, {N, N, W, W}, {N, E, E, N}};
static const uint8_t kForceLeave[4] = {kS, kW, kN, kE};   // leave masks of ForceN..ForceW

// Behaviour of tile codes past the real tile set, stray object types and stray effect frames, measured on the
// original by black-box tests (spec doc 04 §4.4; generator: verify/gen_stray.py).
#include "stray_tables.inc"
#include "draw_tables.inc"

// The cartridge keeps entry masks (codes 00-33) directly followed by leave+flag bytes (bit 7 special,
// bit 6 slide, bit 5 ice, low nibble leave mask). Codes past 33 therefore read the next bytes: the entry
// mask of code 34+k is the leave+flag byte of code k (doc 03 §1).
static uint8_t romLF(uint8_t leave, uint8_t flags, int fSpecial, int fSlide, int fIce) {
    return static_cast<uint8_t>((leave & 0x0F) | ((flags & fSpecial) ? 0x80 : 0) | ((flags & fSlide) ? 0x40 : 0) | ((flags & fIce) ? 0x20 : 0));
}

void Game::syncAlias(int k) {
    if (lvl_->edgesAreWalls || k < 0 || k >= 0x34 || kOddTiles[k].entry >= 0) return;
    props_[0x34 + k].entry = romLF(props_[k].leave, props_[k].flags, F_SPECIAL, F_SLIDE, F_ICE);
}

static Cell byteToCell(uint8_t b);
Game::Game(const LevelData& lvl, Globals& g) : lvl_(&lvl), g_(g) {
    for (int r = 0; r < 32; ++r) rowLo_[r] = static_cast<uint8_t>(r * 32);
    auto set = [&](uint8_t c, uint8_t e, uint8_t l = 0, uint8_t f = 0) { props_[c] = {e, l, f}; };
    for (int c = 0; c < 256; ++c) props_[c] = {0x7F, 0x0F, F_SPECIAL};          // codes >= 0x80 are never tiles
    for (int c = 0; c < Count; ++c) set(c, 0);
    set(Wall, 0x0F); set(Ice, 0, 0, F_SLIDE | F_ICE); set(Dirt, 0x10); set(FakeBlueWall, 0x10);
    for (int k = 0; k < 4; ++k) set(ForceN + k, 0, kForceLeave[k], F_SLIDE);
    set(ForceRandom, 0, 0, F_SLIDE);
    set(IceNW, 0x06, kN | kW, F_SLIDE | F_ICE); set(IceNE, 0x0C, kN | kE, F_SLIDE | F_ICE);
    set(IceSE, 0x09, kE | kS, F_SLIDE | F_ICE); set(IceSW, 0x03, kS | kW, F_SLIDE | F_ICE);
    for (uint8_t c : {Skates, FireBoots, SuctionBoots, Flippers}) set(c, 0x10);
    set(Fire, 0x20); set(Thief, 0x10); set(PopupWall, 0x10); set(ToggleClosed, 0x0F);
    for (uint8_t c : {DoorRed, DoorBlue, DoorYellow, DoorGreen}) set(c, 0x0F, 0, F_SPECIAL);
    set(KeyYellow, 0x10); set(KeyGreen, 0x10); set(Chip, 0x10); set(Socket, 0x1F); set(Exit, 0x10);
    set(HiddenWall, 0x0F, 0, F_SPECIAL); set(InvisibleWall, 0x0F, 0, F_SPECIAL); set(Gravel, 0x40);
    set(ThinE, 0x08, kE); set(ThinS, 0x01, kS); set(ThinSE, 0x09, kE | kS);
    set(Trap, 0, 0x0F); set(Cloner, 0x0F, 0x0F); set(ChipUncounted, 0x10);
    set(RealBlueWall, 0x0F, 0, F_SPECIAL); set(Hint, 0x10);
    fakeNW_ = lvl.edgesAreWalls || std::getenv("CC_FAKE_NW");   // test switch: fake north/west thin walls in strict mode
    if (lvl.edgesAreWalls) {
        set(ThinN, 0x04, kN); set(ThinW, 0x02, kW);          // extended mode only
    } else {
        // Codes 0x34..0x7F: measured behaviour (stray_tables.inc). Codes 0x34..0x67 whose entry mask follows the
        // leave/flag byte of code-0x34 stay coupled to it (syncAlias), so they change when that tile's leave
        // mask changes at run time (suction boots, trap/cloner release).
        for (int c = 0x34; c < 0x80; ++c) {
            const OddTile& o = kOddTiles[c - 0x34];
            props_[c] = {static_cast<uint8_t>(o.entry < 0 ? 0 : o.entry), o.leave,
                         static_cast<uint8_t>((o.special ? F_SPECIAL : 0) | (o.slide ? F_SLIDE : 0) | (o.ice ? F_ICE : 0))};
        }
        for (int k = 0; k < 0x34; ++k) syncAlias(k);
        for (int k = 0; k < 128; ++k)
            props_[0x80 | k] = {kRefTiles[k][0], kRefTiles[k][1],
                                static_cast<uint8_t>((kRefTiles[k][2] ? F_SLIDE : 0) | (kRefTiles[k][3] ? F_ICE : 0))};
        if (fakeNW_) { set(ThinN, 0x04, kN); set(ThinW, 0x02, kW); }   // test switch only (not the cartridge)
    }

    // A map byte with bit 7 set is an object reference to the original, also when the level data holds one with no
    // object there (a "ghost" reference; measured, tools/measure/ghost.py, doc 09 §25)
    for (int c = 0; c < kMapCells; ++c) map_[c] = byteToCell(lvl.map[c]);
    nSlots_ = std::max<int>({kSlots, lvl.maxSlots, static_cast<int>(lvl.state.size())});
    state_.assign(nSlots_, 0); under_.assign(nSlots_, 0); x_.assign(nSlots_, 0); y_.assign(nSlots_, 0);
    timeLimit_ = time_ = lvl.timeLimit;
    for (int c = 0; c < kMapCells; ++c) if (map_[c] == Chip) ++chips_;
    if (lvl.chipsRequired >= 0) chips_ = lvl.chipsRequired;     // DAT levels state their own count

    // Links (doc 02 §5)
    link_.fill(-1);
    for (int c = 0; c < kMapCells; ++c) {
        Cell v = map_[c]; uint8_t target; int stepv;
        if ((v == BrownButton || v == RedButton) && lvl.explicitLinks) continue;
        if (v == BrownButton) { target = Trap; stepv = 1; }
        else if (v == RedButton) { target = Cloner; stepv = 1; }
        else if (v == Teleport) { target = Teleport; stepv = -1; }
        else continue;
        for (int k = 1; k <= kMapCells; ++k) {
            int p = ((c + stepv * k) % kMapCells + kMapCells) % kMapCells;
            if (map_[p] == target) { link_[c] = static_cast<int16_t>(p); break; }
        }
        // A brown/red button with no trap/clone machine anywhere: the original's search never ends and the
        // cartridge hangs while starting the level (doc 02 §5). Strict mode reproduces that as a crash.
        if (link_[c] < 0 && v != Teleport && !lvl.edgesAreWalls) crashed_ = true;
        // The cartridge's link table (two 1024-byte halves, kept in RAM across levels - only source cells are
        // rewritten): buttons store the target's address (0x0C00 + cell), teleports its x and y coordinates.
        // The high half of row 31 is the RAM the map reaches off its top edge (see peek).
        if (link_[c] >= 0) {
            int p = link_[c];
            if (v == Teleport) { g_.linkLo[c] = static_cast<uint8_t>((p % kMapW) * 8); g_.linkHi[c] = static_cast<uint8_t>((p / kMapW) * 8); }
            else { g_.linkLo[c] = static_cast<uint8_t>(p & 0xFF); g_.linkHi[c] = static_cast<uint8_t>(0x0C | (p >> 8)); }
        }
    }
    if (lvl.explicitLinks)
        for (const auto& l : lvl.links)
            if (l.from >= 0 && l.from < kMapCells && l.to >= 0 && l.to < kMapCells) link_[l.from] = l.to;
    // Objects (doc 02 §4 step 6)
    for (int i = static_cast<int>(lvl.state.size()) - 1; i >= 0; --i) {
        state_[i] = lvl.state[i]; x_[i] = lvl.x[i]; y_[i] = lvl.y[i]; under_[i] = 0;
        if (!state_[i]) continue;
        int c = cellOf(i);
        curCell_ = c;                                   // the lookup's last result: slot 0's cell
        if (map_[c] == Trap) state_[i] |= 0x80;
        under_[i] = map_[c];
        map_[c] = objCell(i);
    }
    state_[0] = static_cast<uint8_t>((state_[0] & 0xFC) | S);
    rng_.reset();
    if (crashed_) { dead_ = true; death_ = DeathReason::Crash; waiting_ = false; }
}

uint8_t Game::classMask(int i) const {
    int t = type(i);
    if (t >= 12) return kStrayClass[t - 12][dir(i)];   // stray types (off-map writes only): measured
    if (t == T_NONE) return 0;                          // type 0 (stray "moving" byte 0x80..0x83): enters any
    uint8_t b = (t == T_CHIP) ? 0x00 : (t == T_BLOCK) ? 0x10 : (t == T_FIREBALL) ? 0x50 : 0x70;
    return static_cast<uint8_t>(b | dirBit(dir(i)));
}

int Game::neighbour(int c, int d) const {
    if (lvl_->edgesAreWalls) {                 // extended mode (as Tile World): the map edge is solid
        int r = c / kMapW + kDY[d], col = c % kMapW + kDX[d];
        if (r < 0 || r >= kMapH || col < 0 || col >= kMapW) return kOffMap;
        return r * kMapW + col;
    }
    // The cartridge has no edge test (doc 04 §4.2): the target is simply the cell index -32 / +1 / +32 / -1.
    // Off the top that reaches the 32 bytes of RAM below the map, off the bottom the first 32 object state
    // bytes (see readCell); the object's own coordinates wrap separately on each axis (8-bit).
    static const int kDelta[4] = {-kMapW, 1, kMapW, -1};
    return c + kDelta[d];
}

// The original's RAM as far as the game state goes (doc 04 §4.2-4.3). Map cells outside 0..1023 and corrupted
// link targets address these bytes; anything else is memory this remake does not model, and touching it ends
// the attempt as a crash.
//   0020-0023 boots (skates, suction, fire, flippers)   0026/0027 chips left   0028 level finished
//   002A-002D keys (red, blue, yellow, green)           002F tick              1180/1181 time left
//   0400-07FF link table, low bytes      0800-0BFF link table, high bytes (0BE0-0BFF: "row -1" of the map)
//   0C00-0FFF map                        1000 state  1080 x  1100 y  1200 under   (128 slots each)
// Only off-map moves (0BE0-101F) and corrupted button links (any address) reach these. Other addresses are
// not modelled: reads give 0 (matches every measured case), writes are dropped.
static Cell byteToCell(uint8_t b) { return b & 0x80 ? objCell(b & 0x7F) : b; }
static uint8_t cellToByte(Cell v) { return isObj(v) ? static_cast<uint8_t>(0x80 | (objOf(v) & 0x7F)) : static_cast<uint8_t>(v); }

uint8_t Game::peek(int a) const {
    switch (a) {
    case 0x20: return skates_; case 0x21: return suction_; case 0x22: return fire_; case 0x23: return flippers_;
    case 0x26: return static_cast<uint8_t>(chips_); case 0x27: return static_cast<uint8_t>(chips_ >> 8);
    case 0x28: return finished_;
    case 0x2A: case 0x2B: case 0x2C: case 0x2D: return keys_[a - 0x2A];
    case 0x2F: return g_.tick;
    case 0x4A: return g_.randomForce;          // R lives in the low two bits (test hook; the other bits are not modelled)
    case 0x1180: return static_cast<uint8_t>(time_); case 0x1181: return static_cast<uint8_t>(time_ >> 8);
    default: break;
    }
    if (a >= 0x0400 && a < 0x0800) return g_.linkLo[a - 0x0400];
    if (a >= 0x0800 && a < 0x0C00) return g_.linkHi[a - 0x0800];
    if (a >= 0x0C00 && a < 0x1000) return cellToByte(map_[a - 0x0C00]);
    if (a >= 0x1000 && a < 0x1080) return state_[a - 0x1000];
    if (a >= 0x1080 && a < 0x1100) return static_cast<uint8_t>(x_[a - 0x1080]);
    if (a >= 0x1100 && a < 0x1180) return static_cast<uint8_t>(y_[a - 0x1100]);
    if (a >= 0x1200 && a < 0x1280) return cellToByte(under_[a - 0x1200]);
    if (a >= 0x2F53 && a < 0x2F73) return rowLo_[a - 0x2F53];
    if (a >= 0x3D73 && a < 0x3DA7) return props_[a - 0x3D73].entry;
    if (a >= 0x3DA7 && a < 0x3DDB) { const TileProps& p = props_[a - 0x3DA7]; return romLF(p.leave, p.flags, F_SPECIAL, F_SLIDE, F_ICE); }
    if (staleCells()) flagDesync(1, 1);   // a stale lookup reached RAM whose real contents are unknown here
    return 0;          // RAM not modelled (only corrupted links read it): taken as 0, i.e. "no object"
}

void Game::poke(int a, uint8_t v) {
    switch (a) {
    case 0x20: skates_ = v; return; case 0x21: suction_ = v; return;
    case 0x22: fire_ = v; return;   case 0x23: flippers_ = v; return;
    case 0x26: chips_ = (chips_ & 0xFF00) | v; return;      // e.g. a clone written here changes chips left
    case 0x27: chips_ = (chips_ & 0x00FF) | (v << 8); return;
    case 0x28: finished_ = v; return;
    case 0x4A: g_.randomForce = v & 3; return;
    case 0x2A: case 0x2B: case 0x2C: case 0x2D: keys_[a - 0x2A] = v; return;
    case 0x2F: g_.tick = v; return;
    case 0x1180: time_ = (time_ & 0xFF00) | v; return;
    case 0x1181: time_ = (time_ & 0x00FF) | (v << 8); return;
    default: break;
    }
    if (a >= 0x0400 && a < 0x0800) { g_.linkLo[a - 0x0400] = v; return; }
    if (a >= 0x0800 && a < 0x0C00) { g_.linkHi[a - 0x0800] = v; return; }
    if (a >= 0x0C00 && a < 0x1000) { map_[a - 0x0C00] = byteToCell(v); return; }
    if (a >= 0x1000 && a < 0x1080) {
        state_[a - 0x1000] = v;
        if (a == 0x1000 && !lvl_->edgesAreWalls) {           // Chip's state overwritten: drawing it may damage
            int d = chipDrawDelay(v, g_.tick & 1);             // the program (doc 04 §4.4)
            if (d >= 0 && drawCrashIn_ < 0) drawCrashIn_ = d;
        }
        return;
    }
    if (a >= 0x1080 && a < 0x1100) { x_[a - 0x1080] = v; return; }
    if (a >= 0x1100 && a < 0x1180) { y_[a - 0x1100] = v; return; }
    if (a >= 0x1200 && a < 0x1280) { under_[a - 0x1200] = byteToCell(v); return; }
    if (a == 0x3DE2) { v38_ = v; return; }
    if (a >= 0x2F53 && a < 0x2F73) { rowLo_[a - 0x2F53] = v; return; }   // the cell lookup's row table     // the program byte drawing code 38 overwrites (doc 04 §4.4)
    // tile property tables: entry masks of codes 00-33, then their leave+flag bytes (doc 03 §1)
    if (a >= 0x3D73 && a < 0x3DA7) { props_[a - 0x3D73].entry = v; return; }
    if (a >= 0x3DA7 && a < 0x3DDB) {
        int k = a - 0x3DA7;
        props_[k].leave = v & 0x0F;
        props_[k].flags = static_cast<uint8_t>((v & 0x80 ? F_SPECIAL : 0) | (v & 0x40 ? F_SLIDE : 0) | (v & 0x20 ? F_ICE : 0));
        syncAlias(k);
        return;
    }
    // RAM not modelled: the write is lost
}

Cell Game::readCell(int c) const {
    if (c >= 0 && c < kMapCells) return map_[c];
    return byteToCell(peek((0x0C00 + c) & 0xFFFF));      // 16-bit address arithmetic, as on the 6502
}

void Game::writeCell(int c, Cell v) {
    if (c >= 0 && c < kMapCells) { map_[c] = v; return; }
    poke((0x0C00 + c) & 0xFFFF, cellToByte(v));
}

// Addresses whose contents the memory model holds (see peek/poke).
static bool modelled(int a) {
    if ((a >= 0x20 && a <= 0x23) || a == 0x26 || a == 0x27 || a == 0x28 || (a >= 0x2A && a <= 0x2D) || a == 0x2F) return true;
    if (a >= 0x0400 && a < 0x1280) return a < 0x1180 || a >= 0x1200 || a == 0x1180 || a == 0x1181;
    return (a >= 0x2F53 && a < 0x2F73) || (a >= 0x3D73 && a < 0x3DDB) || a == 0x3DE2;
}

Cell Game::byteToCellAt(int a) const { return (a >= 0x0C00 && a < 0x1000) ? map_[a - 0x0C00] : byteToCell(peek(a)); }

// A button whose link bytes were overwritten by drawing an odd tile code (doc 04 §4.4) points at a screen
// position turned into an address, typically sprite or program memory. The remake reads "no object" there
// (as every stale link of real levels behaves), but the original reads whatever is there - a stray 0x81 in
// sprite memory counts as object 1. Flagged as out of sync.
void Game::checkDrawnLink(int c, int A) const {
    if (lvl_->edgesAreWalls || c < 0 || c >= kMapCells || !linkDrawn_[c]) return;
    if (!(A >= 0x0C00 && A < 0x1000) && !modelled(A & 0xFFFF)) flagDesync(1, 5);
}
void Game::setAt(int a, Cell v) { if (a >= 0x0C00 && a < 0x1000) map_[a - 0x0C00] = v; else poke(a, cellToByte(v)); }

// Target of a button / teleport link. Extended mode uses the level's own wiring; strict mode reads the
// cartridge's link table, so a link byte corrupted by an off-map write sends the button/teleport elsewhere.
int Game::linkAddr(int c) const {
    if (lvl_->explicitLinks || lvl_->edgesAreWalls) return link_[c] < 0 ? -1 : 0x0C00 + link_[c];
    return (peek(0x0800 + c) << 8) | peek(0x0400 + c);       // through the memory model: c can be off the map
}

// ---------------------------------------------------------------- doc 04 §3
bool Game::testMove(int i) {
    if (moveCodeBroken()) { crashed_ = true; return false; }   // the move test runs the code drawing 38 overwrote
    if (dying(i)) return false;
    uint8_t cm = classMask(i);
    int d = dir(i);
    // the leave mask is tested against the mover's class mask (direction bits): for every real type that is
    // its own direction; stray type 0 can leave anything (measured, doc 04 §4.4)
    if (leaveOf(under_[i]) & cm & 0x0F) return false;
    int t = neighbour(cellOf(i), d);
    if (t == kOffMap) return false;
    Cell v = readCell(t);
    if (!isObj(v)) {
        if (flagsOf(v) & F_SPECIAL) return specialBump(i, v, t);
        return !(entryOf(v) & cm);
    }
    int j = objOf(v);
    if (entryOf(under_[j]) & cm) return false;
    if (i != 0) {
        if (dying(j)) {
            // erase the stale effect and test again; with off-map aliasing this can repeat forever, and then the
            // original hangs
            writeCell(t, under_[j]); state_[j] = 0;
            return testMove(i);
        }
        if (j != 0) return false;
        killChipBy(i);
        return false;
    }
    if (dying(j)) return false;
    if (type(j) == T_BLOCK) return pushBlock(j);
    if (type(j) == T_CHIP) return true;
    killChipBy(j);
    return false;
}

void Game::killChipBy(int k) {
    state_[0] = 0x46;
    state_[k] = 0x46;
    death_ = DeathReason::Killed;
    sfx(SFX_DEATH);
}

bool Game::specialBump(int i, Cell v, int t) {
    if (i != 0) return false;
    if (probe_ == 1) return false;
    if (v >= DoorRed && v <= DoorGreen) {
        int k = v - DoorRed;
        if (!keys_[k]) return false;
        if (probe_ == 0 && k != 3) --keys_[k];
        return true;
    }
    if (v == HiddenWall || v == RealBlueWall) writeCell(t, Wall);
    return false;
}

bool Game::pushBlock(int j) {
    pushing_ = true;
    if (!aligned(j) || under_[j] == Cloner) return false;
    state_[j] = static_cast<uint8_t>(0x80 | (T_BLOCK << 2) | dir(0));
    if (!testMove(j)) return false;
    sfx(SFX_PUSH);
    if (probe_ == 1) return false;     // quirk: block already launched (doc 04 §3)
    advance(j);
    return true;
}

// ---------------------------------------------------------------- doc 04 §4
void Game::step(int i) {
    if (dying(i)) return;
    if (type(i) >= 12) {                          // stray types: measured step per direction
        x_[i] = (x_[i] + kStrayStep[type(i) - 12][dir(i)][0]) & 0xFF;
        y_[i] = (y_[i] + kStrayStep[type(i) - 12][dir(i)][1]) & 0xFF;
        return;
    }
    int sp = type(i) == T_BLOB ? 1 : 2;
    const int ox = x_[i], oy = y_[i];
    x_[i] = (x_[i] + kDX[dir(i)] * sp) & 0xFF;      // 8-bit coordinates (wrap at the map edge)
    y_[i] = (y_[i] + kDY[dir(i)] * sp) & 0xFF;
    // An object wrapping across the map edge while a stray object has shifted the cell lookup's row table:
    // the original's lookups there are not mapped (one measured case, objdrawtest 75 with the A-button start).
    if ((std::abs(x_[i] - ox) > 128 || std::abs(y_[i] - oy) > 128) && rowTableShifted()) flagDesync(2, 6);
}

void Game::advance(int i) {
    if (state_[i] == 0) return;
    if (!moving(i)) { handler(i, STAY); return; }
    if (dying(i)) return;
    if (aligned(i)) {
        bool ok = testMove(i);
        if (i == 0) {
            if (ok) g_.bumpLatch = false;
            else if (under_[0] != Trap && !g_.bumpLatch) { g_.bumpLatch = true; sfx(SFX_BUMP); }
        }
        if (!ok) {
            if (!alive(i)) return;
            // A blocked move on 71 runs the same code as standing on it: by the sound-driver byte 795B another
            // object can get an extra step (measured: a tank on 71 facing a wall or another 71). Not modelled: flagged.
            if (under_[i] == 0x71) flagDesync(1, 8);
            if (i == 0 && skates_) { handler(i, STAY); return; }
            if (flagsOf(under_[i]) & F_ICE) { setDir(i, dir(i) ^ 2); handler(i, ARRIVE); return; }
            handler(i, STAY);
            return;
        }
        int c = cellOf(i), t = neighbour(c, dir(i));
        writeCell(c, under_[i]);
        under_[i] = readCell(t);
        writeCell(t, objCell(i));
    }
    if (state_[i] != 0) {
        step(i);
        if (flagsOf(under_[i]) & F_SLIDE) {
            bool extra = true;
            if (i == 0) {
                bool ice = flagsOf(under_[i]) & F_ICE;
                if (ice && skates_) extra = false;
                if (!ice && suction_) extra = false;
            }
            if (extra) step(i);
        }
    }
    if (aligned(i)) {
        if (moveCodeBroken()) { crashed_ = true; return; }   // arrival runs the code drawing 38 overwrote
        handler(i, ARRIVE);
    }
}

// ---------------------------------------------------------------- doc 03 §3
void Game::handler(int i, Event ev) {
    if (dying(i)) return;
    Cell u = under_[i];
    if (isObj(u)) return;
    if (u >= 0x34 && !(fakeNW_ && (u == ThinN || u == ThinW))) {
        // Past the handler table the original jumps into unrelated code (doc 04 §4.4): most codes crash, a few
        // happen to land on code that behaves like a simple handler.
        const OddTile& o = kOddTiles[(u & 0x7F) - 0x34];
        switch (u < 0x80 ? o.kind : 0) {
        case 1: stop(i); return;                                  // stop, like floor
        case 2: return;                                           // keep moving, like a trap without button
        case 3:                                                   // move on at once (ARRIVE): advance again now;
            if (ev == ARRIVE) {                                   // a blocked re-move bounces on ice and arrives
                // again; without end the original runs out of stack and crashes
                // Chip boxed in on such a tile (both ways out blocked) bounces back and forth endlessly; on the
                // original that recursion runs into the stack and what follows depends on it (Chip flips N/S
                // irregularly, other objects get extra moves, sometimes a crash). Not modelled: Chip stays put,
                // flagged as out of sync.
                // Any other object: the original usually crashes (stack overrun), as the remake does after 32 levels,
                // but not always (random survey, doc 09 §22); flagged either way.
                if (redirectDepth_ >= 3 && !lvl_->edgesAreWalls) { flagDesync(1, 4); if (i == 0) return; }
                // A Chip-type object (Chip, or a fake Chip in another slot) arriving on 71: on the original, whether it is
                // moved on at once depends on hidden state, above all a byte of the sound driver's working memory
                // (795B, which follows the music: with it locked at 0 no re-move, at 3C re-moved at once; measured with
                // writes to it blocked, tools/measure/lock71.py, doc 04 §4.4). Not modelled: flagged; the real Chip is
                // re-moved, a fake Chip waits (the commoner outcomes in the tests).
                if (type(i) == T_CHIP && u == 0x71) { flagDesync(1, 8); if (i != 0) return; }
                if (++redirectDepth_ > 32) { crashed_ = true; --redirectDepth_; return; }
                advance(i);
                --redirectDepth_;
                return;
            }
            // An object standing on 71 (STAY): the code it lands in reads the same sound-driver byte (795B) and, by
            // its value, holds Chip back for some ticks (measured with a block resting on 71). Not modelled: flagged.
            if (u == 0x71) flagDesync(1, 8);
            if (o.stay == 2) return;                              // STAY: nothing (keeps moving) ...
            crashed_ = true;                                      // ... or crash
            return;
        default: crashed_ = true; return;
        }
    }
    const bool chip = (i == 0);
    const int ty = type(i);
    switch (u) {
    case Ice:
        if (chip && skates_) { if (ev == ARRIVE) sfx(SFX_BOOTS); stop(i); }
        return;
    case IceNW: case IceNE: case IceSE: case IceSW:
        if (chip && skates_) { if (ev == ARRIVE) sfx(SFX_BOOTS); stop(i); return; }
        setDir(i, kCorner[u - IceNW][dir(i)]);
        // An object standing still on a corner (it started the level there) is only turned, not set moving: a block
        // keeps standing, and Chip, who cannot steer on ice, stays put (measured, tools/measure/fakechip.py controls).
        if (ev == STAY) return;
        setMoving(i);
        sfxChip(i, SFX_SPLASH);
        return;
    case ForceN: case ForceE: case ForceS: case ForceW: case ForceRandom: {
        if (chip && suction_) { if (ev == ARRIVE) sfx(SFX_BOOTS); stop(i); return; }
        int d;
        if (u == ForceRandom) { g_.randomForce = (g_.randomForce + 1) & 3; d = g_.randomForce; }
        else d = u - ForceN;
        setDir(i, d); setMoving(i);
        return;
    }
    case Teleport:
        if (ev == ARRIVE) sfxChip(i, SFX_EXIT);
        teleport(i);
        return;
    case Skates: case FireBoots: case SuctionBoots: case Flippers:
        if (chip) {
            if (u == Skates) skates_ = true;
            else if (u == FireBoots) fire_ = true;
            else if (u == Flippers) flippers_ = true;
            else { suction_ = true; for (int k = 0; k < 4; ++k) { props_[ForceN + k].leave = 0; syncAlias(ForceN + k); } }
            sfx(SFX_PICKUP);
            under_[i] = Floor;
        }
        stop(i);
        return;
    case Fire:
        // slot 0 is treated as Chip whatever its type (a level with no player start puts a monster there):
        // a fireball or block in slot 0 burns too, unless the fire boots are held (measured)
        if (ev == ARRIVE && (chip || (ty != T_FIREBALL && ty != T_BLOCK))) {
            if (chip && fire_) sfx(SFX_FIREWALK);
            else {
                state_[i] = 0x40;
                if (chip) { death_ = DeathReason::Killed; sfx(SFX_DEATH); }
                return;
            }
        }
        stop(i);
        return;
    case Water:
        // slot 0 first, whatever its type: without flippers it drowns, even a glider or a block (measured)
        if (chip && flippers_) { if (ev == ARRIVE) sfx(SFX_SWIM); stop(i); return; }
        if (!chip && ty == T_GLIDER) { stop(i); return; }
        sfx(SFX_SPLASH);
        if (!chip && ty == T_BLOCK) { state_[i] = 0x4C; under_[i] = Dirt; return; }
        state_[i] = 0x4C;
        if (chip) death_ = DeathReason::Killed;
        return;
    case Thief:
        if (ev == ARRIVE && chip) {
            skates_ = suction_ = fire_ = flippers_ = false;
            for (int k = 0; k < 4; ++k) { props_[ForceN + k].leave = kForceLeave[k]; syncAlias(ForceN + k); }
            sfx(SFX_THIEF);
        }
        stop(i);
        return;
    case PopupWall:
        under_[0] = Wall;
        sfxChip(i, SFX_POPUP);
        stop(i);
        return;
    case GreenButton:
        if (ev == ARRIVE) {
            std::swap(props_[ToggleOpen].entry, props_[ToggleClosed].entry);
            swapped_ = !swapped_;
            sfx(SFX_PICKUP);
        }
        stop(i);
        return;
    case DoorRed: case DoorBlue: case DoorYellow: case DoorGreen: case Socket:
        sfxChip(i, SFX_DOOR); sfxChip(i, SFX_CLEAR);
        under_[i] = Floor; stop(i);
        return;
    case Dirt: case FakeBlueWall:
        sfxChip(i, SFX_CLEAR);
        under_[i] = Floor; stop(i);
        return;
    case KeyRed: case KeyBlue: case KeyYellow: case KeyGreen:
        if (chip) { ++keys_[u - KeyRed]; sfx(SFX_PICKUP); under_[i] = Floor; }
        else if (u == KeyBlue) under_[i] = Floor;     // any other object destroys a blue key (doc 03 §3)
        stop(i);
        return;
    case BlueButton:
        if (ev == ARRIVE) { tankReverse_ ^= 1; sfx(SFX_PICKUP); }
        stop(i);
        return;
    case Chip: case ChipUncounted:
        if (u == Chip && ev == ARRIVE && i != 0) {
            // Any object other than slot 0 arriving on a counted chip (only Chip-type and stray objects can enter
            // one; measured): the chip is counted, but it stays on the map, the mover keeps moving, Chip's own
            // moving flag is cleared (even mid-step) and the rest of this tick's movement loop is skipped. The pickup's
            // "tile under the collector becomes floor" also lands on slot 0 (written before its state; visible only
            // when Chip stands on something other than floor, e.g. ice: Jacques 292 with edge protection).
            if (chips_ > 0) --chips_;
            under_[0] = Floor;
            state_[0] &= 0x7F;
            abortMoves_ = true;
            return;
        }
        if (ev == ARRIVE) {
            if (chips_ > 0) --chips_;
            sfxChip(i, SFX_PICKUP);
            under_[i] = Floor;
        }
        stop(i);
        return;
    case Exit:
        if (chip && !finished_) { finished_ = true; sfx(SFX_EXIT); }
        stop(i);
        return;
    case Bomb:
        if (ev == ARRIVE) {
            sfx(SFX_DEATH);
            state_[i] = 0x40; under_[i] = Floor;
            if (chip) death_ = DeathReason::Killed;
            return;
        }
        stop(i);
        return;
    case Trap:
        if (ev == ARRIVE) sfx(SFX_BUMP);
        return;                         // keeps moving flag
    case Cloner:
        if (ev == ARRIVE) sfx(SFX_BUMP);
        return;
    case BrownButton: {
        if (ev == ARRIVE) sfx(SFX_PICKUP);
        if (moveCodeBroken()) { crashed_ = true; return; }   // the cell lookup runs the code drawing 38 overwrote
        int A = linkAddr(cellOf(i));
        checkDrawnLink(cellOf(i), A);
        if (staleCells()) curCell_ = A - 0x0C00;      // the lookup's last result is now the link address
        Cell tv = A < 0 ? Cell(Floor) : byteToCellAt(A);
        if (isObj(tv)) {
            int k = objOf(tv);
            props_[Trap].leave = 0; syncAlias(Trap); advance(k); props_[Trap].leave = 0x0F; syncAlias(Trap);
        }
        stop(i);
        return;
    }
    case RedButton: {
        if (ev != ARRIVE) { stop(i); return; }
        if (moveCodeBroken()) { crashed_ = true; return; }   // the cell lookup runs the code drawing 38 overwrote
        int A = linkAddr(cellOf(i));
        checkDrawnLink(cellOf(i), A);
        if (staleCells()) curCell_ = A - 0x0C00;      // the lookup's last result is now the link address
        Cell tv = A < 0 ? Cell(Floor) : byteToCellAt(A);
        if (isObj(tv)) {
            int k = objOf(tv);
            uint8_t ss = state_[k]; Cell su = under_[k]; int sx = x_[k], sy = y_[k];
            props_[Cloner].leave = 0; syncAlias(Cloner); advance(k); props_[Cloner].leave = 0x0F; syncAlias(Cloner);
            stop(i);
            if (isObj(byteToCellAt(A))) return;
            for (int s = 1; s < nSlots_; ++s) {
                if (state_[s] == 0) {
                    state_[s] = ss; x_[s] = sx; y_[s] = sy; under_[s] = su;
                    setAt(A, objCell(s));
                    sfx(SFX_DOOR);
                    break;
                }
            }
            return;
        }
        stop(i);
        return;
    }
    default:
        stop(i);
        return;
    }
}

// ---------------------------------------------------------------- doc 04 §6
void Game::teleport(int i) {
    const int ox = x_[i], oy = y_[i];
    if (moveCodeBroken()) { crashed_ = true; return; }       // the cell lookup runs the code drawing 38 overwrote
    if (staleCells()) {
        // Stale cell lookup (code 38 at x = 96, doc 04 §4.4), measured: an object arriving on a teleport while
        // moving east or west makes the original hang. Moving north or south, its under-tile goes to the stale
        // cell and it lands at (0, 0), still moving. If the stale cell has a non-empty link, or the cell beyond
        // it is blocked, the original's search instead wanders through memory the remake does not track and
        // ends somewhere else: flagged as out of sync.
        int d = dir(i);
        if (d == E || d == W) { crashed_ = true; return; }
        int c = curCell_;
        writeCell(c, under_[i]);
        if (peek(0x0400 + c) || peek(0x0800 + c)) flagDesync(1, 3);
        Cell ahead = readCell(neighbour(c, d));
        if (isObj(ahead) || (entryOf(ahead) & classMask(i))) flagDesync(1, 3);
        x_[i] = 0; y_[i] = 0;
        return;
    }
    // The original loops until it finds a free teleport; with a corrupted or stale link table it may never
    // find one, and then it hangs (doc 04 §6, §4.4).
    for (int guard = 0; guard < 4 * kMapCells; ++guard) {
        int c = cellOf(i);
        writeCell(c, under_[i]);
        if (lvl_->explicitLinks || lvl_->edgesAreWalls) {
            int L = link_[c];
            if (L < 0) { stop(i); return; }
            x_[i] = (L % kMapW) * 8; y_[i] = (L / kMapW) * 8;
        } else {
            x_[i] = peek(0x0400 + c); y_[i] = peek(0x0800 + c);  // stored as coordinates
        }
        int L = cellOf(i);
        if (readCell(L) != Teleport) continue;      // occupied (or not a teleport at all): go on from there
        under_[i] = Teleport; writeCell(L, objCell(i));
        probe_ = 0x80; bool ok = testMove(i); probe_ = 0;
        if (ok) return;
        if (!alive(i)) return;
        if (x_[i] == ox && y_[i] == oy) { stop(i); return; }
    }
    crashed_ = true;
}

// ---------------------------------------------------------------- doc 04 §9
void Game::ai(int i) {
    const int ty = type(i);
    int d = dir(i);
    auto tryList = [&](const int* rel, int n) {
        for (int k = 0; k < n; ++k) {
            int r = rel[k];
            if (r == 4) r = rng_.next() & 3;
            d = (d + r) & 3;
            setDir(i, d); setMoving(i);
            if (testMove(i)) return;
            if (!alive(i)) return;
        }
    };
    static const int bug[] = {3, 1, 1, 1}, para[] = {1, 3, 3, 3}, fireball[] = {0, 1, 2, 3},
                     glider[] = {0, 3, 2, 1}, ball[] = {0, 2}, walker[] = {0, 4},
                     tankFwd[] = {0}, tankBack[] = {2};
    switch (ty) {
    case T_BUG: tryList(bug, 4); break;
    case T_PARAMECIUM: tryList(para, 4); break;
    case T_FIREBALL: tryList(fireball, 4); break;
    case T_GLIDER: tryList(glider, 4); break;
    case T_BALL: tryList(ball, 2); break;
    case T_WALKER: tryList(walker, 2); break;
    case T_TANK: tryList(tankReverse_ == 2 ? tankBack : tankFwd, 1); break;
    case T_BLOB: setDir(i, (rng_.next() ^ g_.tick) & 3); setMoving(i); break;
    case T_TEETH: {
        if (!(g_.tick & 4)) return;
        int dx = x_[i] - x_[0], dy = y_[i] - y_[0];
        int horiz = dx >= 0 ? W : E, vert = dy >= 0 ? N : S;
        int p, q, sd;
        if (std::abs(dx) > std::abs(dy)) { p = horiz; q = vert; sd = std::abs(dy); }
        else { p = vert; q = horiz; sd = std::abs(dx); }
        setDir(i, p); setMoving(i);
        if (testMove(i)) return;
        if (!alive(i)) return;
        if (sd != 0 && state_[i] != 0) { setDir(i, q); setMoving(i); }
        break;
    }
    default: break;
    }
}

// ---------------------------------------------------------------- doc 05 §2
static int startDir(uint8_t pref) {
    switch (pref) {
        case kN: return N; case kE: return E; case kS: return S; case kW: return W;
        case kE | kW: return E; case kN | kW: return W; case kN | kE: return E; case kN | kE | kW: return N;
        case kS | kN: return N; case kS | kE: return E; case kS | kW: return W; case kS | kE | kW: return S;
        case kS | kN | kW: return W; case kS | kN | kE: return E; case kN | kE | kS | kW: return E;
        default: return N;
    }
}

void Game::chipDecide(uint8_t held) {
    if (state_[0] == 0) return;
    if (under_[0] == Teleport) return;
    if ((flagsOf(under_[0]) & F_ICE) && !skates_) return;
    if (!aligned(0)) return;
    if ((g_.lastChoice & 0x80) && moving(0)) { g_.lastChoice = 0; return; }
    pushing_ = false;
    if (!held) { g_.bumpLatch = false; return; }
    uint8_t newly = held & ~g_.prevDirs;
    g_.prevDirs = held;
    if (newly) g_.preferred = newly;
    int d = startDir(g_.preferred);
    uint8_t pending = held;
    for (;;) {
        if (pending & dirBit(d)) {
            pending &= ~dirBit(d);
            state_[0] = static_cast<uint8_t>(0x80 | (T_CHIP << 2) | d);
            if (testMove(0)) { g_.lastChoice = state_[0]; return; }
            if (!alive(0)) return;
            pushing_ = true;
        }
        if (!pending) break;
        d = (d + 1) & 3;
    }
    state_[0] = static_cast<uint8_t>(0x80 | (T_CHIP << 2) | d);
    g_.lastChoice = state_[0];
}

void Game::removeObject(int i) {
    // doc 04 §8: an object standing on another object's reference is left alone entirely; otherwise its
    // reference is looked for at its cell, then east, then south. The original keeps probing the south cell
    // forever when it is not there (it hangs) - only possible after stray writes off the map edge.
    if (isObj(under_[i])) return;
    if (moveCodeBroken()) { crashed_ = true; return; }  // the cell lookup runs the code drawing 38 overwrote
    int c = cellOf(i);
    for (int cc : {c, c + 1, c + kMapW}) {
        if (readCell(cc) == objCell(i)) { writeCell(cc, under_[i]); state_[i] = 0; under_[i] = 0; return; }
    }
    if (!lvl_->edgesAreWalls) { crashed_ = true; return; }
    state_[i] = 0; under_[i] = 0;
}

// ---------------------------------------------------------------- doc 04 §2
void Game::doTick(uint8_t held) {
    g_.tick = static_cast<uint8_t>(g_.tick + 1);
    probe_ = 1;
    for (int k = 0; k < nSlots_; ++k) {
        int i = (k == nSlots_ - 1) ? 0 : nSlots_ - 1 - k;   // 127..1 then 0
        uint8_t st = state_[i];
        if (i != 0 && (st == 0 || (st & 0x80))) continue;
        if (st & 0x40) {
            if (g_.tick & 1) {
                int f = st & 0x3F;
                uint8_t next = kEffectNext[f];            // frames 0x12+ exist only as stray bytes (measured)
                state_[i] = next;                         // the original stores the new state first,
                if (!next) removeObject(i);               // then removes the finished effect
            }
            continue;
        }
        if (aligned(i)) {
            // Dispatch on the slot's *type* (doc 04 §2): normally slot 0 is Chip and no other slot is, but
            // stray bytes written off the map edge can change that.
            switch (type(i)) {
                case T_NONE: break;
                case T_CHIP: chipDecide(held); break;     // always acts on slot 0
                case 13: rng_.next(); break;              // the dispatch entry for type 13 is the RNG step
                case 12: case 14: case 15: crashed_ = true; break;
                default: ai(i); break;
            }
        }
        if (crashed_) return;
    }
    probe_ = 0;
    abortMoves_ = false;
    for (int i = nSlots_ - 1; i >= 0 && !crashed_ && !abortMoves_; --i) advance(i);
    if (crashed_) return;
    if (time_) {
        if (++g_.subSecond >= 20) {
            g_.subSecond = 0;
            if (--time_ == 0) { state_[0] = 0x46; death_ = DeathReason::TimeOut; }
        }
    }
}

void Game::tick(const Input& in) {
    sounds_.clear();
    if (drawCrashIn_ > 0 && --drawCrashIn_ == 0) crashed_ = true;   // damage from drawing a junk Chip lands now
    if (!lvl_->edgesAreWalls) {                                      // program code damaged by drawing 61 / 6E
        if (hit61_) crashed_ = true;
        if (v6E_ >= 0 && (k6EDelay[v6E_] == 1 || frames_ % 6 == 0)) crashed_ = true;
    }
    ++frames_;
    if (waiting_ && (in.dirs || in.ab)) waiting_ = false;
    if (chips_ == 0) props_[Socket].entry = 0x10;
    if (running() && !crashed_) doTick(in.dirs);
    if (drawCrashIn_ == 0) crashed_ = true;                           // value whose drawing crashes at once
    if (!crashed_ && !lvl_->edgesAreWalls && displayWouldHang()) crashed_ = true;
    if (crashed_ && !dead_) { dead_ = true; death_ = DeathReason::Crash; return; }
    if (!lvl_->edgesAreWalls && !noDraw_) drawPass();
    if (finished_ && state_[0]) removeObject(0);
    if (!finished_ && !dead_ && state_[0] == 0) {
        if (--grace_ < 0) {
            dead_ = true;
            // the original starts every attempt with its death-reason byte at "time-out"; a Chip that vanishes
            // without a recorded cause (stray writes off the map edge) is therefore reported as a time-out
            if (death_ == DeathReason::None) death_ = DeathReason::TimeOut;
        }
    }
    static const uint8_t kTankNext[4] = {0, 2, 0, 1};
    tankReverse_ = kTankNext[tankReverse_];
}

// The original draws the 11 x 11 cells around its camera every frame (doc 06 §4.1). For a cell holding an
// object it follows the chain cell -> object -> that object's under-tile -> ... until it reaches a tile.
// Off-map writes (doc 04 §4.2) can make that chain loop, and the original then hangs while drawing.
bool Game::displayWouldHang() const {
    auto clampq = [](int q) { return std::clamp(q, 0, 93); };
    int cx = clampq(x_[0] / 2 - 16), cy = clampq(y_[0] / 2 - 16);
    int c0 = (cx >> 2) - 1, r0 = (cy >> 2) - 1;    // measured: 11 x 11 cells centred on the camera
    for (int r = r0; r < r0 + 11; ++r)
        for (int c = c0; c < c0 + 11; ++c) {
            int addr = r * kMapW + c;                       // linear, like the original's address arithmetic
            Cell v = (addr >= 0 && addr < kMapCells) ? map_[addr] : map_[0];
            int steps = 0;
            while (isObj(v)) {
                if (++steps > kSlots) return true;          // more links than objects: a cycle
                v = under_[objOf(v) & 0x7F];
            }
        }
    return false;
}

// Drawing a tile first writes the cell's screen position into the tile's sprite block. For codes 34-7F the
// block lookup runs past its table, so the four bytes (x, y as 16-bit values, x = 12*col - 3*cx + 27) land on a
// fixed address per code (doc 04 §4.4). The 11 x 11 cells are drawn bottom-right first, so where two cells write
// the same address the first cell in reading order wins. Codes whose address is game data are repeated here
// through the memory model; codes whose address is program code that runs are remembered as damage.
// Measured (tools/measure/objaddr.py): object states whose drawing write lands on memory the remake models.
// Object states (low 7 bits) whose drawing write lands in program code, the stack or zero-page scratch
// (measured, tools/measure/objaddr.py): 3C-3F, 52-7F except 68, 73, 75.
[[maybe_unused]] static const bool kDrawsIntoCode[128] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1,1,1,1,1,1,1,1};

static int objDrawAddr(uint8_t s) {
    if (s == 0) return -1;
    switch (s & 0x7F) {            // bit 7 does not change the sprite looked up
        case 0x68: return 0x1045;   // slot state table, slots 69-72
        case 0x75: return 0x2F63;   // the cell lookup's row table, rows 16-19
        default: return -1;
    }
}

void Game::drawPass() {
    auto clampq = [](int q) { return std::clamp(q, 0, 93); };
    int cx = clampq(x_[0] / 2 - 16), cy = clampq(y_[0] / 2 - 16);
    int c0 = (cx >> 2) - 1, r0 = (cy >> 2) - 1;
    for (int r = r0 + 10; r >= r0; --r)
        for (int c = c0 + 10; c >= c0; --c) {
            int addr = r * kMapW + c;
            Cell v = (addr >= 0 && addr < kMapCells) ? map_[addr] : map_[0];
            for (int steps = 0; isObj(v) && steps <= kSlots; ++steps) v = under_[objOf(v) & 0x7F];
            if (isObj(v) || v < 0x34 || v >= 0x80) continue;
            const OddDraw& od = kOddDraw[v - 0x34];
            // codes 67 and 6C write into sound data (the ice-slide patch / music voice 3; doc 08 §3): play is
            // unaffected, the player is only told the cartridge would sound different
            if ((v == 0x67 || v == 0x6C) && !soundGlitch_) soundGlitch_ = static_cast<uint8_t>(v);
            int x = 12 * c - 3 * cx + 27, y = 12 * r - 3 * cy + 27;
            switch (od.kind) {
                case 1:
                    for (int b = 0; b < 4; ++b) {
                        int la = od.addr + b;
                        if (la >= 0x0400 && la < 0x0C00) linkDrawn_[(la - 0x0400) & 0x3FF] = true;
                    }
                    poke(od.addr, static_cast<uint8_t>(x)); poke(od.addr + 1, static_cast<uint8_t>(x >> 8));
                    poke(od.addr + 2, static_cast<uint8_t>(y)); poke(od.addr + 3, static_cast<uint8_t>(y >> 8));
                    break;
                case 2: hit61_ = true; break;
                case 3: v6E_ = x & 0xFF; break;
                case 4: v38_ = x & 0xFF; break;
                default: break;
            }
        }
    // Objects are drawn after the tiles, found through the object references in the drawn cells (reading order):
    // an object whose reference has been lost is not drawn. An object in a stray state looks up a sprite block
    // past its table and first writes its screen position there (measured, tools/measure/objaddr.py); the states
    // whose write lands on game data are repeated here. Chip's own junk states: chipDrawDelay.
    // Measured (tools/measure/objscan.py): the object pass looks up only the window's LAST row through the cell
    // lookup, base = 256 * (row / 8) + T[row] + c0, and reaches the rows above by stepping back 32 cells each; it
    // visits base - 32 * (10 - m) + k (m, k = 0..10) in reading order. Every visited map byte with bit 7 set is
    // taken as an object reference; addresses outside the map (the link table below, the object table above) are
    // skipped (tools/measure/objscan.py edge probes). So a
    // shifted entry T[last row] moves the whole scanned window by the shift, in cells. The table runs on past
    // row 31 (rows 32..35, normal values, never written by the row-table writer). A stray object's position
    // write happens whether or not it is on screen.
    const int lastRow = r0 + 10;
    auto rowEntry = [&](int r) { return r < 32 ? rowLo_[r] : static_cast<uint8_t>(r * 32); };
    const int base = 256 * (lastRow >> 3) + rowEntry(lastRow) + c0;
    for (int m = 0; m <= 10; ++m)
        for (int k = 0; k <= 10; ++k) {
            int addr = base - 32 * (10 - m) + k;
            if (addr < 0 || addr >= kMapCells) continue;   // measured: nothing outside the map is taken as an object
            uint8_t b = cellToByte(map_[addr]);
            if (!(b & 0x80)) continue;
            int i = b & 0x7F, a = objDrawAddr(state_[i]);
            // state 7B writes into program code at A7F9; the Lynx then usually crashes a few ticks later, during a
            // screen scroll (4 of 5 measured cases, tools/measure/drawtest.py 47; the crash tick is not predictable;
            // doc 04 §4.4). Other states that write into code (kDrawsIntoCode) occur in real levels without any
            // visible effect, so only this one is flagged.
            if (i != 0 && (state_[i] & 0x7F) == 0x7B) flagDesync(3, 7);
            if (a < 0) continue;
            int x = 3 * (x_[i] / 2 - cx) + 27, y = 3 * (y_[i] / 2 - cy) + 27;
            poke(a, static_cast<uint8_t>(x)); poke(a + 1, static_cast<uint8_t>(x >> 8));
            poke(a + 2, static_cast<uint8_t>(y)); poke(a + 3, static_cast<uint8_t>(y >> 8));
        }
    curCell_ = (r0 - 1) * kMapW + c0 + 10;          // where the drawing loop leaves the lookup's result
    // 6E's damage sits in the tile-animation code: until the crash it comes due (up to 5 ticks), animated tiles in
    // view can have their screen position written to addresses that depend on the damage and on what else is
    // running (measured: water with x = 30 lands on 00B2, 10B2 or 20B2). Not modelled; flagged as out of sync.
    if (v6E_ >= 0 && k6EDelay[v6E_] == 6 && !outOfSync_)
        for (int r = r0; r <= r0 + 10 && !outOfSync_; ++r)
            for (int c = c0; c <= c0 + 10; ++c) {
                int addr = r * kMapW + c;
                Cell v = (addr >= 0 && addr < kMapCells) ? map_[addr] : map_[0];
                for (int steps = 0; isObj(v) && steps <= kSlots; ++steps) v = under_[objOf(v) & 0x7F];
                if (v == Teleport || v == Fire || v == Water || v == Exit) { flagDesync(1, 2); break; }
            }
}

uint8_t Game::loopSound() const {
    if (!running() || state_[0] == 0 || dying(0)) return 0;
    const TileProps& p = pr(under_[0]);
    if ((p.flags & F_ICE) && !skates_) return SFX_ICE_LOOP;
    if ((p.flags & F_SLIDE) && !(p.flags & F_ICE) && !suction_) return SFX_FORCE_LOOP;
    return 0;
}

bool Game::chipOnHint() const {
    return state_[0] && !dying(0) && under_[0] == Hint && aligned(0);
}

} // namespace cc
