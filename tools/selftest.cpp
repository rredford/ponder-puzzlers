// Self-test: validates a user ROM against the spec's vectors and replays a TWS file
// against the oracle table (spec doc 09). Usage: selftest ROM.lnx [solutions.tws oracle.tsv]
#include <cstdio>
#include <fstream>
#include <map>
#include <sstream>
#include "core/engine.hpp"
#include "core/rom.hpp"
#include "core/tws.hpp"

using namespace cc;

struct Oracle { std::string outcome; long tick = -1; };

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "usage: %s ROM.lnx [solutions.tws oracle.tsv]\n", argv[0]); return 2; }
    Rom rom(argv[1]);
    int fails = 0;
    std::printf("ROM body CRC-32 %08X %s\n", rom.bodyCrc32(), rom.bodyCrc32() == 0x6A5F53EDu ? "(matches spec)" : "(DIFFERENT dump)");
    struct V { int n; size_t len; uint32_t crc; } vec[] = {{2, 29577, 0x5AB859A4u}, {22, 1487, 0x40B91E56u}, {0, 3640, 0x37509E02u}};
    for (auto& v : vec) {
        const Bytes& f = rom.file(v.n);
        bool ok = f.size() == v.len && crc32(f.data(), f.size()) == v.crc;
        std::printf("file %3d: %s\n", v.n, ok ? "ok" : "MISMATCH"); fails += !ok;
    }
    auto pw = generatePasswords();
    bool pwok = pw[0] == "BDHP" && pw[1] == "JXMJ" && pw[2] == "ECBQ" && pw[149] == "GNLP";
    std::printf("passwords: %s\n", pwok ? "ok" : "MISMATCH"); fails += !pwok;
    LevelData l1 = parseLevel(rom.levelFile(1), 1);
    bool l1ok = l1.title == "LESSON 1" && l1.timeLimit == 100 && l1.hint.size() == 5;
    std::printf("level 1: '%s' time %d hint lines %zu %s\n", l1.title.c_str(), l1.timeLimit, l1.hint.size(), l1ok ? "ok" : "MISMATCH");
    fails += !l1ok;

    if (argc >= 4) {
        TwsFile tws = loadTws(argv[2]);
        std::map<int, Oracle> oracle;
        std::ifstream of(argv[3]); std::string line;
        while (std::getline(of, line)) {
            if (line.empty() || line[0] == '#') continue;
            std::istringstream ss(line); int lv, tt; Oracle o; std::string tk;
            ss >> lv >> tt >> o.outcome >> tk;
            if (!tk.empty()) o.tick = std::stol(tk);
            oracle[lv] = o;
        }
        int pass = 0, total = 0;
        for (auto& sol : tws.solutions) {
            if (sol.level < 1 || sol.level > kLevelSlots || !oracle.count(sol.level)) continue;
            ++total;
            LevelData lvl = parseLevel(rom.levelFile(sol.level), sol.level);
            Globals g; g.tick = 0x05; g.randomForce = 0; g.subSecond = 0;   // doc 09 §6 protocol
            if (tws.ruleset == 1) g.randomForce = twsSlideToR(sol.slide);   // the solution's initial random-floor direction
            Game game(lvl, g);
            std::map<uint32_t, uint8_t> input;
            for (auto& m : sol.moves) input[m.tick] |= twsDirToMask(m.dir);
            uint32_t end = sol.moves.empty() ? 0 : sol.moves.back().tick + 400;
            std::string outcome = "stall"; long at = -1;
            for (uint32_t t = 0; t < end; ++t) {
                Input in; auto it = input.find(t); if (it != input.end()) in.dirs = it->second; in.ab = (t == 0);   // Tile World starts the level at tick 0
                game.tick(in);
                if (game.finished()) { outcome = "win"; at = t; break; }
                if (game.dead()) { outcome = game.deathReason() == DeathReason::TimeOut ? "time-out" : "death"; at = t; break; }
            }
            const Oracle& o = oracle[sol.level];
            bool ok = o.outcome == outcome && o.tick == at;
            pass += ok;
            if (!ok) std::printf("level %3d: got %s @%ld, expected %s @%ld\n", sol.level, outcome.c_str(), at, o.outcome.c_str(), o.tick);
        }
        std::printf("replays: %d/%d match the oracle\n", pass, total);
        fails += total - pass;
    }
    std::printf("%s\n", fails ? "SELFTEST FAILED" : "SELFTEST PASSED");
    return fails ? 1 : 0;
}
