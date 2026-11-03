// Tile World solution file (.tws) reader — used for regression tests and demo playback.
#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace cc {

struct TwsMove { uint32_t tick; uint16_t dir; };   // dir: 0 N, 1 W, 2 S, 3 E, 4 NW, 5 SW, 6 NE, 7 SE

struct TwsSolution {
    int level = 0;
    std::string password;
    uint32_t totalTicks = 0;
    int slide = 0;                   // initial random-force-floor direction (TWS dir code 0 N, 1 W, 2 S, 3 E)
    std::vector<TwsMove> moves;
};

struct TwsFile {
    int ruleset = 0;                 // 1 = Lynx, 2 = MS
    std::string setName;
    std::vector<TwsSolution> solutions;
};

TwsFile loadTws(const std::string& path);
// The cartridge's random-force-floor counter for a Lynx-ruleset solution's slide direction (the counter cycles
// N=0, E=1, S=2, W=3; doc 09 §6). MS-ruleset files carry a fixed value with no meaning for the cartridge.
inline uint8_t twsSlideToR(int slide) { static const uint8_t m[4] = {0, 3, 2, 1}; return m[slide & 3]; }
// Converts a TWS direction to the engine's DirBit mask.
uint8_t twsDirToMask(uint16_t d);

} // namespace cc
