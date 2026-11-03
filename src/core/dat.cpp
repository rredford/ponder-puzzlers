#include "dat.hpp"
#include "engine.hpp"
#include "rom.hpp"
#include <cstdio>
#include <fstream>
#include <iterator>
#include <stdexcept>

namespace cc {
using namespace tile;

const LevelData* LevelSet::find(int number) const {
    for (const auto& l : levels) if (l.number == number) return &l;
    return nullptr;
}

LevelSet cartridgeLevels(const Rom& rom) {
    LevelSet s;
    s.name = "Cartridge";
    s.fromCartridge = true;
    s.mainCount = kLastMainLevel;
    for (int n = 1; n <= kLevelSlots; ++n) s.levels.push_back(parseLevel(rom.levelFile(n), n));
    return s;
}

// ---------------------------------------------------------------- tile mapping
// MS/DAT object code -> Lynx tile code (0xFF = not a plain tile)
static uint8_t msToLynxTile(uint8_t m, bool* approx) {
    *approx = false;
    switch (m) {
        case 0x00: return Floor;       case 0x01: return Wall;        case 0x02: return Chip;
        case 0x03: return Water;       case 0x04: return Fire;        case 0x05: return InvisibleWall;
        case 0x08: return ThinS;       case 0x09: return ThinE;       case 0x30: return ThinSE;
        case 0x0B: return Dirt;        case 0x0C: return Ice;         case 0x0D: return ForceS;
        case 0x12: return ForceN;      case 0x13: return ForceE;      case 0x14: return ForceW;
        case 0x32: return ForceRandom; case 0x15: return Exit;
        case 0x16: return DoorBlue;    case 0x17: return DoorRed;     case 0x18: return DoorGreen;
        // Ice corners: MSCC names a corner by its two OPEN sides ("SE ice slide" turns you south/east), the
        // Lynx tile set by its two WALL sides - so each maps to the opposite corner.
        case 0x19: return DoorYellow;  case 0x1A: return IceNW;       case 0x1B: return IceNE;
        case 0x1C: return IceSE;       case 0x1D: return IceSW;       case 0x1E: return FakeBlueWall;
        case 0x1F: return RealBlueWall; case 0x21: return Thief;      case 0x22: return Socket;
        case 0x23: return GreenButton; case 0x24: return RedButton;   case 0x25: return ToggleClosed;
        case 0x26: return ToggleOpen;  case 0x27: return BrownButton; case 0x28: return BlueButton;
        case 0x29: return Teleport;    case 0x2A: return Bomb;        case 0x2B: return Trap;
        case 0x2C: return HiddenWall;  case 0x2D: return Gravel;      case 0x2E: return PopupWall;
        case 0x2F: return Hint;        case 0x31: return Cloner;
        case 0x64: return KeyBlue;     case 0x65: return KeyRed;      case 0x66: return KeyGreen;
        case 0x67: return KeyYellow;   case 0x68: return Flippers;    case 0x69: return FireBoots;
        case 0x6A: return Skates;      case 0x6B: return SuctionBoots;
        // MSCC-only codes with no Lynx counterpart (unused codes, drowned/burned/exited-Chip and exit animation
        // frames, out-of-range values) become plain wall, as in Tile World's Lynx mode.
        case 0x36: case 0x37: return InvisibleWall;      // "not used" codes that MSCC treats as invisible wall
        default: *approx = true; return Wall;
    }
}

// MS creature code -> (Lynx type, Lynx direction); type 0 if not a creature
static bool msCreature(uint8_t m, int* type, int* dir) {
    static const int msDir[4] = {N, W, S, E};
    if (m == 0x0A) { *type = T_BLOCK; *dir = N; return true; }
    if (m >= 0x0E && m <= 0x11) { *type = T_BLOCK; *dir = msDir[m - 0x0E]; return true; }
    if (m >= 0x3C && m <= 0x3F) { *type = T_CHIP; *dir = msDir[m - 0x3C]; return true; }   // swimming Chip
    if (m >= 0x6C && m <= 0x6F) { *type = T_CHIP; *dir = msDir[m - 0x6C]; return true; }
    if (m < 0x40 || m > 0x63) return false;
    static const int types[9] = {T_BUG, T_FIREBALL, T_BALL, T_TANK, T_GLIDER, T_TEETH, T_WALKER, T_BLOB, T_PARAMECIUM};
    *type = types[(m - 0x40) / 4];
    *dir = msDir[(m - 0x40) % 4];
    return true;
}

static uint8_t lynxToMsTile(uint8_t t) {
    switch (t) {
        case Floor: return 0x00; case Wall: return 0x01; case Chip: case ChipUncounted: return 0x02;
        case Water: return 0x03; case Fire: return 0x04; case InvisibleWall: return 0x05;
        case ThinS: return 0x08; case ThinE: return 0x09; case ThinSE: return 0x30;
        case Dirt: return 0x0B; case Ice: return 0x0C; case ForceS: return 0x0D; case ForceN: return 0x12;
        case ForceE: return 0x13; case ForceW: return 0x14; case ForceRandom: return 0x32; case Exit: return 0x15;
        case DoorBlue: return 0x16; case DoorRed: return 0x17; case DoorGreen: return 0x18; case DoorYellow: return 0x19;
        case IceNW: return 0x1A; case IceNE: return 0x1B; case IceSE: return 0x1C; case IceSW: return 0x1D;
        case FakeBlueWall: return 0x1E; case RealBlueWall: return 0x1F; case Thief: return 0x21; case Socket: return 0x22;
        case GreenButton: return 0x23; case RedButton: return 0x24; case ToggleClosed: return 0x25; case ToggleOpen: return 0x26;
        case BrownButton: return 0x27; case BlueButton: return 0x28; case Teleport: return 0x29; case Bomb: return 0x2A;
        case Trap: return 0x2B; case HiddenWall: return 0x2C; case Gravel: return 0x2D; case PopupWall: return 0x2E;
        case Hint: return 0x2F; case Cloner: return 0x31; case ThinN: return 0x06; case ThinW: return 0x07;
        case KeyBlue: return 0x64; case KeyRed: return 0x65; case KeyGreen: return 0x66; case KeyYellow: return 0x67;
        case Flippers: return 0x68; case FireBoots: return 0x69; case Skates: return 0x6A; case SuctionBoots: return 0x6B;
        default: return 0x00;
    }
}

static uint8_t lynxToMsCreature(int type, int dir) {
    static const int msIndex[4] = {0, 3, 2, 1};      // Lynx N,E,S,W -> MS N,W,S,E index
    int k = msIndex[dir & 3];
    switch (type) {
        case T_CHIP: return static_cast<uint8_t>(0x6C + k);
        case T_BLOCK: return 0x0A;
        case T_BUG: return static_cast<uint8_t>(0x40 + k);
        case T_FIREBALL: return static_cast<uint8_t>(0x44 + k);
        case T_BALL: return static_cast<uint8_t>(0x48 + k);
        case T_TANK: return static_cast<uint8_t>(0x4C + k);
        case T_GLIDER: return static_cast<uint8_t>(0x50 + k);
        case T_TEETH: return static_cast<uint8_t>(0x54 + k);
        case T_WALKER: return static_cast<uint8_t>(0x58 + k);
        case T_BLOB: return static_cast<uint8_t>(0x5C + k);
        case T_PARAMECIUM: return static_cast<uint8_t>(0x60 + k);
        default: return 0x00;
    }
}

// Custom optional field (ignored by other programs): exact cartridge object slots.
// Records of 4 bytes: slot, state byte, column, row.
static constexpr uint8_t kSlotField = 0x4C;
static constexpr uint8_t kEndMarkerField = 0x4D;   // our extension: slot is the cartridge's end-of-main-sequence marker

// ---------------------------------------------------------------- reading
namespace {
struct Reader {
    const std::vector<uint8_t>& d; size_t p; size_t end;
    uint8_t u8() { if (p >= end) throw std::runtime_error("DAT: truncated level"); return d[p++]; }
    uint16_t u16() { uint16_t lo = u8(); return static_cast<uint16_t>(lo | (u8() << 8)); }
};
}

static std::vector<uint8_t> decodeLayer(Reader& r, size_t len) {
    std::vector<uint8_t> out;
    size_t stop = r.p + len;
    while (r.p < stop && out.size() < kMapCells) {
        uint8_t b = r.u8();
        if (b == 0xFF) { uint8_t n = r.u8(), v = r.u8(); out.insert(out.end(), n, v); }
        else out.push_back(b);
    }
    r.p = stop;
    out.resize(kMapCells, 0);
    return out;
}

static std::string cstr(const std::vector<uint8_t>& d, size_t p, size_t n, uint8_t xr = 0) {
    std::string s;
    for (size_t i = 0; i < n && p + i < d.size(); ++i) {
        uint8_t c = d[p + i] ^ xr;
        if (c == 0 || (xr && d[p + i] == 0)) break;
        s += static_cast<char>(c);
    }
    return s;
}

LevelSet loadDat(const std::string& path, DatReport* report, const DatOptions& opt) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("cannot open " + path);
    std::vector<uint8_t> d((std::istreambuf_iterator<char>(f)), {});
    auto slash = path.find_last_of("/\\");
    return loadDatBytes(d, slash == std::string::npos ? path : path.substr(slash + 1), report, opt);
}

LevelSet loadDatBytes(const std::vector<uint8_t>& d, const std::string& name, DatReport* report, const DatOptions& opt) {
    if (d.size() < 6) throw std::runtime_error("DAT: file too short");
    uint32_t magic = d[0] | (d[1] << 8) | (d[2] << 16) | (uint32_t(d[3]) << 24);
    if ((magic & 0xFFFF) != 0xAAAC) throw std::runtime_error("not a DAT level file");
    int count = d[4] | (d[5] << 8);
    LevelSet set;
    set.name = name;
    DatReport rep;
    size_t p = 6;
    for (int lv = 0; lv < count; ++lv) {
        if (p + 2 > d.size()) throw std::runtime_error("DAT: truncated file");
        size_t len = d[p] | (d[p + 1] << 8);
        Reader r{d, p + 2, p + 2 + len};
        if (r.end > d.size()) throw std::runtime_error("DAT: truncated level record");
        p = r.end;
        LevelData L;
        L.number = r.u16();
        L.timeLimit = r.u16();
        L.chipsRequired = r.u16();
        r.u16();                                   // map detail flag
        auto top = decodeLayer(r, r.u16());
        auto bottom = decodeLayer(r, r.u16());
        size_t optLen = r.u16(), optEnd = r.p + optLen;
        std::vector<std::pair<int, int>> monsterOrder;
        struct SlotRec { int slot, state, col, row; };
        std::vector<SlotRec> slotRecs;
        std::vector<LevelData::Link> traps, clones;
        while (r.p + 2 <= optEnd) {
            uint8_t type = r.u8(), flen = r.u8();
            size_t fp = r.p;
            switch (type) {
                case 3: L.title = cstr(d, fp, flen); break;
                case 6: L.password = cstr(d, fp, flen, 0x99); break;
                case 8: L.password = cstr(d, fp, flen); break;
                case 7: L.hint.push_back(cstr(d, fp, flen)); break;
                case 1: if (flen >= 2) L.timeLimit = d[fp] | (d[fp + 1] << 8); break;
                case 4: for (size_t k = 0; k + 10 <= flen; k += 10) {
                            auto w = [&](size_t o) { return d[fp + k + o] | (d[fp + k + o + 1] << 8); };
                            traps.push_back({int16_t(w(2) * kMapW + w(0)), int16_t(w(6) * kMapW + w(4))});
                        } break;
                case 5: for (size_t k = 0; k + 8 <= flen; k += 8) {
                            auto w = [&](size_t o) { return d[fp + k + o] | (d[fp + k + o + 1] << 8); };
                            clones.push_back({int16_t(w(2) * kMapW + w(0)), int16_t(w(6) * kMapW + w(4))});
                        } break;
                case 10: for (size_t k = 0; k + 2 <= flen; k += 2) monsterOrder.push_back({d[fp + k], d[fp + k + 1]}); break;
                case kSlotField: for (size_t k = 0; k + 4 <= flen; k += 4)
                                     slotRecs.push_back({d[fp + k], d[fp + k + 1], d[fp + k + 2], d[fp + k + 3]});
                                 break;
                case kEndMarkerField: L.endMarker = true; break;
                default: break;
            }
            r.p = fp + flen;
        }
        // Hints in DAT files are one string; word-wrap it into display lines of <= 34 characters.
        if (L.hint.size() == 1) {
            std::string h = L.hint[0], cur, word;
            L.hint.clear();
            auto flushWord = [&]() {
                if (word.empty()) return;
                if (!cur.empty() && cur.size() + 1 + word.size() > 34) { L.hint.push_back(cur); cur.clear(); }
                cur += (cur.empty() ? "" : " ") + word;
                word.clear();
            };
            for (char ch : h) { if (ch == ' ' || ch == '\n') flushWord(); else word += ch; }
            flushWord();
            if (!cur.empty()) L.hint.push_back(cur);
        }

        // Build the Lynx map: bottom layer under creatures, top layer otherwise.
        struct Obj { int type, dir, cell; };
        std::vector<Obj> objs;
        std::vector<int> oddCount(256, 0);
        // Thin walls on north/west edges (MS codes 06/07) do not exist on the Lynx. Each is re-expressed as a
        // south/east edge of the neighbouring cell; that blocks exactly the same crossing.
        std::vector<int> northEdge, westEdge;
        auto tileOf = [&](uint8_t code, int c, bool* approx) -> uint8_t {
            if (code == 0x06) { *approx = false; if (opt.extended) return ThinN; northEdge.push_back(c); return Floor; }
            if (code == 0x07) { *approx = false; if (opt.extended) return ThinW; westEdge.push_back(c); return Floor; }
            uint8_t t = msToLynxTile(code, approx);
            if (*approx) ++oddCount[code];
            return t;
        };
        for (int c = 0; c < kMapCells; ++c) {
            int type, dir; bool approx = false;
            uint8_t t = top[c], b = bottom[c], tileCode;
            if (msCreature(t, &type, &dir)) {
                objs.push_back({type, dir, c});
                if (msCreature(b, &type, &dir)) { tileCode = Floor; approx = true;
                    rep.warnings.push_back("level " + std::to_string(L.number) + ": creature buried under a creature removed"); }
                else tileCode = tileOf(b, c, &approx);
            } else {
                tileCode = tileOf(t, c, &approx);
            }
            if (approx) ++rep.approximatedTiles;
            L.map[c] = tileCode;
        }
        auto addEdge = [&](int cell, bool south) -> bool {
            uint8_t& m = L.map[cell];
            uint8_t want = south ? ThinS : ThinE;
            if (m == Floor) { m = want; return true; }
            if (m == want || m == ThinSE) return true;
            if (m == (south ? ThinE : ThinS)) { m = ThinSE; return true; }
            return m == Wall || m == RealBlueWall;     // edge against a solid wall changes nothing
        };
        int lostEdges = 0;
        for (int c : northEdge) if (c >= kMapW && !addEdge(c - kMapW, true)) ++lostEdges;
        for (int c : westEdge) if (c % kMapW > 0 && !addEdge(c - 1, false)) ++lostEdges;
        if (lostEdges) {
            rep.approximatedTiles += lostEdges;
            rep.warnings.push_back("level " + std::to_string(L.number) + ": " + std::to_string(lostEdges) +
                                   " north/west thin wall(s) next to a tile that cannot carry the edge - dropped");
        }
        for (int k = 0; k < 256; ++k)
            if (oddCount[k]) {
                char buf[96];
                std::snprintf(buf, sizeof buf, "level %d: %d x MSCC-only tile 0x%02X -> wall", L.number, oddCount[k], k);
                rep.warnings.push_back(buf);
            }

        // Chips required: the Lynx counts chip tiles when a level starts. When a DAT asks for fewer chips than
        // the map holds, turn the surplus (last in reading order) into the uncounted chip tile, which looks and
        // behaves the same but is not counted - so the level is exactly expressible on the cartridge.
        {
            int total = 0;
            for (int c = 0; c < kMapCells; ++c) if (L.map[c] == Chip) ++total;
            if (L.chipsRequired >= 0 && L.chipsRequired <= total) {
                for (int c = kMapCells - 1, extra = total - L.chipsRequired; c >= 0 && extra > 0; --c)
                    if (L.map[c] == Chip) { L.map[c] = ChipUncounted; --extra; }
                L.chipsRequired = -1;
            } else if (L.chipsRequired > total) {
                // The cartridge has no chips-required field: it counts the chip tiles. Strict mode does the same
                // (the socket opens after the chips there are); extended mode keeps the DAT's number, as Tile World.
                rep.warnings.push_back("level " + std::to_string(L.number) + ": asks for " + std::to_string(L.chipsRequired) +
                                       " chips but has only " + std::to_string(total) +
                                       (opt.extended ? " (socket can never open)" : " (strict: the cartridge counts " + std::to_string(total) + ")"));
                if (!opt.extended) L.chipsRequired = -1;
            }
        }

        // Assign object slots.
        L.state.assign(kSlots, 0); L.x.assign(kSlots, 0); L.y.assign(kSlots, 0);
        if (opt.extended) { L.maxSlots = kMaxExtendedSlots; L.edgesAreWalls = true; }
        auto place = [&](int slot, uint8_t state, int cell) {
            L.state[slot] = state; L.x[slot] = static_cast<uint8_t>((cell % kMapW) * 8); L.y[slot] = static_cast<uint8_t>((cell / kMapW) * 8);
        };
        if (!slotRecs.empty()) {                    // exact cartridge slots (our export)
            for (auto& s : slotRecs) if (s.slot < kSlots) place(s.slot, static_cast<uint8_t>(s.state), s.row * kMapW + s.col);
        } else {
            // Slot order as Tile World's Lynx mode builds it: every creature and block in reading order, then
            // Chip swapped into slot 0 (the object that was in slot 0 takes Chip's place). The DAT monster list
            // is not used by the Lynx rules.
            std::vector<Obj> order;
            int chipAt = -1;
            for (auto& o : objs) {
                if (o.type == T_CHIP) {
                    if (chipAt >= 0) { rep.warnings.push_back("level " + std::to_string(L.number) + ": extra player start removed"); continue; }
                    chipAt = static_cast<int>(order.size());
                }
                order.push_back(o);
            }
            if (chipAt < 0) rep.warnings.push_back("level " + std::to_string(L.number) + ": no player start");
            else std::swap(order[0], order[chipAt]);
            const size_t limit = opt.extended ? kMaxExtendedSlots : kSlots;
            if (order.size() > limit) {
                rep.warnings.push_back("level " + std::to_string(L.number) + ": " + std::to_string(order.size()) +
                                       " objects; only " + std::to_string(limit) + " slots, the rest were removed");
                order.resize(limit);
            }
            if (order.size() > kSlots) {
                L.state.resize(order.size(), 0); L.x.resize(order.size(), 0); L.y.resize(order.size(), 0);
            }
            for (size_t k = 0; k < order.size(); ++k) {
                uint8_t st = static_cast<uint8_t>((order[k].type << 2) | order[k].dir);
                if (L.map[order[k].cell] == Cloner && k > 0) st |= 0x80;     // cloner template (doc 02 §2.2)
                place(static_cast<int>(k), st, order[k].cell);
            }
        }
        // Button wiring. Extended: the DAT's connection lists, as Tile World's Lynx mode (a button that is not
        // listed is not connected). Strict: the cartridge rule (next trap / cloner in reading order) - report
        // buttons whose designed wiring that changes.
        std::vector<LevelData::Link> datLinks = traps;
        datLinks.insert(datLinks.end(), clones.begin(), clones.end());
        if (opt.extended) {
            L.explicitLinks = true;
            L.links = datLinks;
        } else if (!slotRecs.empty()) {
            // our own cartridge export: wiring already follows the cartridge rule
        } else {
            int differ = 0;
            for (int c = 0; c < kMapCells; ++c) {
                uint8_t v = L.map[c];
                if (v != BrownButton && v != RedButton) continue;
                uint8_t target = v == BrownButton ? Trap : Cloner;
                int pos = -1, ex = -1;
                for (int k = 1; k <= kMapCells; ++k) { int q = (c + k) % kMapCells; if (L.map[q] == target) { pos = q; break; } }
                for (auto& l : datLinks) if (l.from == c && l.to >= 0 && l.to < kMapCells && L.map[l.to] == target) ex = l.to;
                if (pos != ex) ++differ;
            }
            {
                bool hasTrap = false, hasCloner = false, brown = false, red = false;
                for (int c = 0; c < kMapCells; ++c) {
                    hasTrap |= L.map[c] == Trap; hasCloner |= L.map[c] == Cloner;
                    brown |= L.map[c] == BrownButton; red |= L.map[c] == RedButton;
                }
                if ((brown && !hasTrap) || (red && !hasCloner))
                    rep.warnings.push_back("level " + std::to_string(L.number) + ": " + (red && !hasCloner ? "red button(s) but no clone machine" : "brown button(s) but no trap") +
                                           " - the original cartridge hangs when this level starts (strict mode: cartridge crash)");
            }
            if (differ) rep.warnings.push_back("level " + std::to_string(L.number) + ": " + std::to_string(differ) +
                                               " button(s) rewired to the cartridge rule (next trap/cloner in reading order)");
        }
        set.levels.push_back(std::move(L));
    }
    rep.levels = static_cast<int>(set.levels.size());
    set.extended = opt.extended;
    set.mainCount = rep.levels;
    for (const auto& L : set.levels) if (L.endMarker) { set.mainCount = L.number - 1; break; }
    if (report) *report = rep;
    return set;
}

// ---------------------------------------------------------------- writing
static void put16(std::vector<uint8_t>& o, int v) { o.push_back(v & 0xFF); o.push_back((v >> 8) & 0xFF); }

static std::vector<uint8_t> encodeLayer(const std::vector<uint8_t>& cells) {
    std::vector<uint8_t> out;
    for (size_t i = 0; i < cells.size();) {
        size_t j = i;
        while (j < cells.size() && cells[j] == cells[i] && j - i < 255) ++j;
        size_t n = j - i;
        if (n >= 4 || cells[i] == 0xFF) { out.push_back(0xFF); out.push_back(static_cast<uint8_t>(n)); out.push_back(cells[i]); }
        else out.insert(out.end(), n, cells[i]);
        i = j;
    }
    return out;
}

void saveDat(const std::string& path, const std::vector<LevelData>& levels, const std::vector<std::string>& passwords) {
    std::vector<uint8_t> out = {0xAC, 0xAA, 0x02, 0x01};     // 0x0102AAAC: Lynx-ruleset level set
    put16(out, static_cast<int>(levels.size()));
    int number = 0;
    for (const LevelData& src : levels) {
        ++number;
        // A DAT cannot have gaps, so an end marker is written as a tiny placeholder level (start next to
        // the exit) tagged with kEndMarkerField; this keeps later level numbers equal to the cartridge's.
        LevelData L = src;
        if (L.endMarker) {
            L.map.fill(Wall); L.state.assign(kSlots, 0); L.x.assign(kSlots, 0); L.y.assign(kSlots, 0);
            const int c = 15 * kMapW + 15;
            L.map[c] = Floor; L.map[c + 1] = Exit;
            L.state[0] = (T_CHIP << 2) | 1; L.x[0] = 15 * 8; L.y[0] = 15 * 8;
            if (L.title.empty()) L.title = "End of the main levels";
            L.hint.clear(); L.timeLimit = 0; L.chipsRequired = 0;
        }
        std::vector<uint8_t> top(kMapCells), bottom(kMapCells, 0);
        for (int c = 0; c < kMapCells; ++c) top[c] = lynxToMsTile(L.map[c]);
        int counted = 0;
        for (int c = 0; c < kMapCells; ++c) if (L.map[c] == Chip) ++counted;
        std::vector<uint8_t> slotField, monsters;
        for (int i = 0; i < static_cast<int>(L.state.size()) && i < 256; ++i) {
            if (!L.state[i]) continue;
            int col = L.x[i] / 8, row = L.y[i] / 8, cell = row * kMapW + col;
            int type = (L.state[i] >> 2) & 15, dir = L.state[i] & 3;
            bottom[cell] = top[cell];
            static const int kMsDirIdx[4] = {0, 3, 2, 1};
            top[cell] = (type == T_BLOCK && L.map[cell] == Cloner) ? static_cast<uint8_t>(0x0E + kMsDirIdx[dir])
                                                                   : lynxToMsCreature(type, dir);
            slotField.insert(slotField.end(), {static_cast<uint8_t>(i), L.state[i], static_cast<uint8_t>(col), static_cast<uint8_t>(row)});
            if (i > 0 && type != T_BLOCK) { monsters.push_back(static_cast<uint8_t>(col)); monsters.push_back(static_cast<uint8_t>(row)); }
        }
        std::vector<uint8_t> opt;
        auto field = [&](uint8_t type, const std::vector<uint8_t>& data) {
            opt.push_back(type); opt.push_back(static_cast<uint8_t>(data.size()));
            opt.insert(opt.end(), data.begin(), data.end());
        };
        auto zstr = [](const std::string& s, uint8_t xr) {
            std::vector<uint8_t> v; for (char ch : s) v.push_back(static_cast<uint8_t>(ch) ^ xr); v.push_back(0); return v;
        };
        field(3, zstr(L.title.substr(0, 63), 0));
        if (L.endMarker) field(kEndMarkerField, {1});
        if (!L.hint.empty()) {
            std::string h;
            for (auto& line : L.hint) { if (!h.empty()) h += ' '; h += line; }
            field(7, zstr(h.substr(0, 127), 0));
        }
        std::string pw = !L.password.empty() ? L.password
                        : (number - 1 < static_cast<int>(passwords.size()) ? passwords[number - 1] : "AAAA");
        field(6, zstr(pw, 0x99));
        // Cartridge links are positional (doc 02 §5); write them explicitly so any program agrees.
        std::vector<uint8_t> traps, clones;
        for (int c = 0; c < kMapCells; ++c) {
            uint8_t v = L.map[c];
            if (v != BrownButton && v != RedButton) continue;
            uint8_t target = v == BrownButton ? Trap : Cloner;
            int to = -1;
            if (L.explicitLinks) { for (auto& l : L.links) if (l.from == c) to = l.to; }
            else for (int k = 1; k <= kMapCells; ++k) { int q = (c + k) % kMapCells; if (L.map[q] == target) { to = q; break; } }
            if (to < 0) continue;
            auto& dst = v == BrownButton ? traps : clones;
            int rec[5] = {c % kMapW, c / kMapW, to % kMapW, to / kMapW, 0};
            for (int k = 0; k < (v == BrownButton ? 5 : 4); ++k) put16(dst, rec[k]);
        }
        for (size_t k = 0; k < traps.size(); k += 250) field(4, std::vector<uint8_t>(traps.begin() + k, traps.begin() + std::min(traps.size(), k + 250)));
        for (size_t k = 0; k < clones.size(); k += 248) field(5, std::vector<uint8_t>(clones.begin() + k, clones.begin() + std::min(clones.size(), k + 248)));
        for (size_t k = 0; k < monsters.size(); k += 254) field(10, std::vector<uint8_t>(monsters.begin() + k, monsters.begin() + std::min(monsters.size(), k + 254)));
        for (size_t k = 0; k < slotField.size(); k += 252)
            field(kSlotField, std::vector<uint8_t>(slotField.begin() + k, slotField.begin() + std::min(slotField.size(), k + 252)));
        if (L.timeLimit > 999) field(1, {static_cast<uint8_t>(L.timeLimit & 0xFF), static_cast<uint8_t>(L.timeLimit >> 8)});

        std::vector<uint8_t> rec;
        put16(rec, number);
        put16(rec, L.timeLimit > 999 ? 999 : L.timeLimit);
        put16(rec, L.chipsRequired >= 0 ? L.chipsRequired : counted);
        put16(rec, 1);
        auto lt = encodeLayer(top), lb = encodeLayer(bottom);
        put16(rec, static_cast<int>(lt.size())); rec.insert(rec.end(), lt.begin(), lt.end());
        put16(rec, static_cast<int>(lb.size())); rec.insert(rec.end(), lb.begin(), lb.end());
        put16(rec, static_cast<int>(opt.size())); rec.insert(rec.end(), opt.begin(), opt.end());
        put16(out, static_cast<int>(rec.size()));
        out.insert(out.end(), rec.begin(), rec.end());
    }
    std::ofstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("cannot write " + path);
    f.write(reinterpret_cast<const char*>(out.data()), static_cast<std::streamsize>(out.size()));
}

} // namespace cc
