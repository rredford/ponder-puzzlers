// Standard Chip's Challenge level-set files (.dat / .dac data files, as used by MSCC and Tile World).
#pragma once
#include <string>
#include <vector>
#include "level.hpp"

namespace cc {

struct LevelSet {
    std::string name;
    std::vector<LevelData> levels;     // levels[i].number == i + 1 for DAT sets
    bool fromCartridge = false;
    // Number of levels in the main sequence; finishing level `mainCount` ends the game.
    int mainCount = 0;
    bool extended = false;             // loaded in extended Lynx mode
    const LevelData* find(int number) const;
};

struct DatReport {
    int levels = 0;
    int approximatedTiles = 0;          // MS-only tiles converted to the nearest Lynx equivalent
    std::vector<std::string> warnings;
};

// How DAT levels are mapped onto the Lynx rules.
//   strict (default): only what the original cartridge can hold - buttons wired by reading order, north/west
//                     thin walls re-expressed as south/east edges (or dropped), at most 128 objects.
//   extended:         as Tile World's Lynx mode - the DAT's button wiring, north/west thin walls, up to 2048
//                     objects. Everything else plays by the same Lynx rules.
struct DatOptions { bool extended = false; };

// Reads a DAT file. Throws std::runtime_error on malformed input.
LevelSet loadDat(const std::string& path, DatReport* report = nullptr, const DatOptions& opt = {});
LevelSet loadDatBytes(const std::vector<uint8_t>& data, const std::string& name, DatReport* report = nullptr,
                      const DatOptions& opt = {});
// Writes levels as a DAT file (Lynx-ruleset signature 0x0102AAAC). `passwords` supplies codes for
// levels whose LevelData::password is empty (index = number - 1).
void saveDat(const std::string& path, const std::vector<LevelData>& levels,
             const std::vector<std::string>& passwords);

// Builds the level set from a cartridge image (levels 1-144 main, 146-149 bonus via password).
LevelSet cartridgeLevels(const class Rom& rom);

} // namespace cc
