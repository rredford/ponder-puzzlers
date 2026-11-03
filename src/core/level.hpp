// Level data, text charset and password generator (spec doc 02, doc 06 §6).
#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <vector>
#include "rom.hpp"

namespace cc {

constexpr int kMapW = 32, kMapH = 32, kMapCells = kMapW * kMapH;
constexpr int kSlots = 128;
constexpr int kFirstLevel = 1, kLastMainLevel = 144, kLevelSlots = 150;

struct LevelData {
    int number = 0;                     // 1-based
    bool endMarker = false;             // slots 145 / 150
    std::array<uint8_t, kMapCells> map{};
    std::vector<uint8_t> state = std::vector<uint8_t>(kSlots, 0),     // object slots (doc 02 §3); the cartridge has 128
                         x = std::vector<uint8_t>(kSlots, 0),
                         y = std::vector<uint8_t>(kSlots, 0);
    int timeLimit = 0;                  // seconds, 0 = untimed
    std::string title;                  // decoded to ASCII
    std::vector<std::string> hint;      // decoded lines
    // ---- extensions for non-cartridge level sources (DAT files, built-in levels)
    std::string password;               // empty = use the generated cartridge password
    int chipsRequired = -1;             // -1 = count 0x23 tiles (cartridge rule, doc 02 §2.1)
    struct Link { int16_t from, to; };  // explicit button -> trap/cloner links (cell indices)
    bool explicitLinks = false;         // true: use `links` for brown/red buttons
    std::vector<Link> links;
    int maxSlots = kSlots;
    bool edgesAreWalls = false;         // extended mode: the map edge blocks (cartridge: movement wraps)              // object slots available while playing (extended mode: more than 128)
};

LevelData parseLevel(const Bytes& file, int number);
// The inverse: a cartridge-format level file (doc 02 §2). Text is upper-cased into the game charset and
// trimmed so the file stays within the cartridge's level buffer (title + hints <= 126 bytes).
Bytes buildLevelFile(const LevelData& level);
constexpr size_t kHintLineChars = 19, kHintLines = 7, kMaxTitleChars = 19;
uint8_t asciiToCharset(char c);

// Game charset <-> ASCII (doc 06 §6.1).
char charsetToAscii(uint8_t c);
std::string decodeText(const uint8_t* p, size_t n);

// The 16-bit generator shared by passwords and creature AI (doc 02 §6.1).
struct Rng {
    uint8_t lo = 0, hi = 0;
    void reset() { lo = hi = 0; }
    uint8_t next();
};

// Passwords for levels 1..150 (index 0 = level 1) (doc 02 §6.2).
std::vector<std::string> generatePasswords();

} // namespace cc
