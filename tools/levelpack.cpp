#include <cstdlib>
// levelpack — level-set utility.
//   levelpack export ROM.lnx out.dat        convert your cartridge's levels to a DAT file (personal use)
//   levelpack info set.dat                  list levels
//   levelpack verify set.dat sol.tws oracle.tsv   replay solutions against an outcome table
//   levelpack check set.dat moves.txt       run move scripts (one line per level: "N: UULLRR..") and require wins
//   levelpack replay set.dat sol.tws        outcome of every solution (oracle TSV format)
//   levelpack lynx set.dat dir              write cartridge-format level files (strict mode) for testing
//   levelpack links set.dat                 buttons whose DAT wiring differs from the cartridge rule
// Add --extended to use extended Lynx mode instead of strict Lynx ROM rules.
//   levelpack raw level.bin script.txt      lock-step test hook (cartridge-format level, pokes, ticks)
#include <cstdio>
#include <fstream>
#include <map>
#include <memory>
#include <iterator>
#include <sstream>
#include <string>
#include "core/dat.hpp"
#include "core/engine.hpp"
#include "core/rom.hpp"
#include "core/tws.hpp"

using namespace cc;

// Test hook (--link-init FILE): the link table's contents when the level starts, 2048 bytes (low half, high
// half). The original never clears this RAM; to compare against outcomes recorded on the emulated cartridge,
// start from the same leftover bytes. The game itself starts with an empty table.
static std::vector<uint8_t> gLinkInit;
static void applyLinkInit(Globals& g) {
    if (gLinkInit.size() != 2048) return;
    for (int k = 0; k < 1024; ++k) { g.linkLo[k] = gLinkInit[k]; g.linkHi[k] = gLinkInit[1024 + k]; }
}

static std::string outcomeOf(Game& g, long t, long* at) {
    if (g.finished()) { *at = t; return "win"; }
    if (g.dead()) { *at = t; return g.deathReason() == DeathReason::TimeOut ? "time-out" : g.deathReason() == DeathReason::Crash ? "crash" : "death"; }
    return "";
}

// Plays a move script: each letter U/D/L/R = one step (held until Chip leaves his cell, then waits until he
// is idle again); '.' = wait 4 ticks. Returns "win"/"death"/"time-out"/"stuck".
static std::string playScript(const LevelData& L, const std::string& moves, long* ticks) {
    Globals g;
    Game game(L, g);
    long t = 0;
    auto tick = [&](uint8_t dirs) { Input in; in.dirs = dirs; game.tick(in); ++t; };
    for (char ch : moves) {
        uint8_t d = ch == 'U' ? kN : ch == 'D' ? kS : ch == 'L' ? kW : ch == 'R' ? kE : 0;
        if (ch == '.') { for (int k = 0; k < 4; ++k) tick(0); }
        else if (d) {
            int sx = game.objX(0), sy = game.objY(0);
            int guard = 0;
            while (game.objX(0) == sx && game.objY(0) == sy && guard++ < 12 && !game.finished() && !game.dead()) tick(d);
            // wait until aligned and not moving (sliding finished)
            guard = 0;
            while (((game.objX(0) | game.objY(0)) & 7 || (game.objState(0) & 0x80)) && guard++ < 400 && !game.finished() && !game.dead()) tick(0);
        } else continue;
        long at; std::string o = outcomeOf(game, t, &at);
        if (!o.empty()) { *ticks = t; return o; }
    }
    for (int k = 0; k < 40; ++k) { tick(0); long at; std::string o = outcomeOf(game, t, &at); if (!o.empty()) { *ticks = t; return o; } }
    *ticks = t;
    return "stuck";
}

int main(int argc, char** argv) {
    if (argc < 3) {
        std::fprintf(stderr, "usage:\n  %s export ROM.lnx out.dat\n  %s info set.dat\n"
                     "  %s verify set.dat solutions.tws oracle.tsv\n  %s check set.dat moves.txt\n", argv[0], argv[0], argv[0], argv[0]);
        return 2;
    }
    std::string cmd = argv[1];
    try {
        if (cmd == "raw" && argc >= 4) {   // lock-step test hook: raw cartridge level file + script
            // script lines: "globals TICK R SUB", "poke ADDR VAL" (hex), "tick DIRMASK" (DirBit mask, hex)
            std::ifstream f(argv[2], std::ios::binary);
            Bytes data((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
            LevelData L;
            std::string fn = argv[2];
            if (fn.size() > 4 && fn.substr(fn.size() - 4) == ".dat") {      // a DAT: its first level, strict or --extended
                DatOptions o; DatReport rp;
                for (int k = 4; k < argc; ++k) if (std::string(argv[k]) == "--extended") o.extended = true;
                L = loadDat(fn, &rp, o).levels.at(0);
            } else L = parseLevel(data, 1);
            Globals g;
            std::ifstream sc(argv[3]);
            std::string line;
            std::vector<std::pair<int, int>> pokes;
            std::unique_ptr<Game> game;
            auto ensure = [&]() { if (!game) { game.reset(new Game(L, g)); } };
            int t = 0; bool syncReported = false, endReported = false;
            while (std::getline(sc, line)) {
                std::istringstream is(line); std::string w; is >> w;
                if (w == "globals") {
                    int a, b, c, p = 0, q = 0, r = 0, bl = 1; is >> a >> b >> c >> p >> q >> r; if (!(is >> bl)) bl = 1;
                    g.tick = a; g.randomForce = b; g.subSecond = c; g.prevDirs = p; g.preferred = q; g.lastChoice = r; g.bumpLatch = bl != 0;
                }
                else if (w == "link") { int a, v; is >> std::hex >> a >> v; if (a < 0x400) g.linkLo[a] = v; else g.linkHi[a - 0x400] = v; }
                else if (w == "nodraw") { ensure(); game->debugNoDraw(); }
                else if (w == "dump") { ensure(); int a, n; is >> std::hex >> a >> n; std::printf("D %x", a); for (int k = 0; k < n; ++k) std::printf(" %02x", game->debugPeek(a + k)); std::printf("\n"); }
                else if (w == "poke") { ensure(); int a, v; is >> std::hex >> a >> v; game->debugPoke(a, static_cast<uint8_t>(v)); }
                else if (w == "tick") {
                    ensure(); int m; is >> std::hex >> m; Input in; in.dirs = static_cast<uint8_t>(m & 0x0F); in.ab = (m & 0x10) != 0;   // bit 4: A/B button
                    game->tick(in);
                    if (std::getenv("CC_SFX")) {                       // sound check: effects started this tick, loop state
                        std::printf("S %d", t);
                        for (uint8_t id : game->sounds()) std::printf(" %02x", id);
                        std::printf(" L%02x\n", game->loopSound());
                    }
                    if (std::getenv("CC_OUTCOME") && !endReported && (game->finished() || game->dead())) {
                        endReported = true;
                        std::printf("O %d %s\n", t, game->finished() ? "win" : game->deathReason() == DeathReason::Crash ? "crash" : game->deathReason() == DeathReason::TimeOut ? "time-out" : "death");
                    }
                    std::printf("T %d %s", t++, game->dead() && game->deathReason() == DeathReason::Crash ? "crash" : "ok");
                    for (int a : {0x1000, 0x1080, 0x1100, 0x1200, 0x0C00}) {
                        int n = a == 0x0C00 ? 1024 : 128;
                        std::printf(" ");
                        for (int k = 0; k < n; ++k) std::printf("%02x", game->debugPeek(a + k));
                    }
                    std::printf("\n");
                    if (game->outOfSync() && !syncReported) { std::printf("F %d outofsync\n", t - 1); syncReported = true; }
                    if (game->dead() && game->deathReason() == DeathReason::Crash) break;
                }
            }
            return 0;
        }
        if (cmd == "export" && argc >= 4) {
            Rom rom(argv[2]);
            LevelSet set = cartridgeLevels(rom);
            auto pw = generatePasswords();
            std::vector<LevelData> out;
            for (auto& L : set.levels) {
                // keep the end marker at 145 (as a tagged placeholder) so bonus levels stay 146-149; drop 150
                if (L.endMarker && L.number == kLevelSlots) continue;
                LevelData c = L;
                c.password = pw[L.number - 1];
                out.push_back(c);
            }
            saveDat(argv[3], out, pw);
            std::printf("wrote %zu levels to %s (personal use only - do not redistribute)\n", out.size(), argv[3]);
            return 0;
        }
        DatReport rep;
        DatOptions dopt;                          // --extended: extended Lynx mode (default: strict Lynx ROM)
        for (int a = 3; a < argc; ++a) {
            if (std::string(argv[a]) == "--extended") dopt.extended = true;
            if (std::string(argv[a]) == "--link-init" && a + 1 < argc) {
                std::ifstream lf(argv[a + 1], std::ios::binary);
                gLinkInit.assign(std::istreambuf_iterator<char>(lf), std::istreambuf_iterator<char>());
            }
        }
        if (cmd == "links") dopt.extended = true;
        LevelSet set = loadDat(argv[2], &rep, dopt);
        if (cmd == "info") {
            std::printf("%s: %d levels, %d approximated tiles\n", set.name.c_str(), rep.levels, rep.approximatedTiles);
            for (auto& w : rep.warnings) std::printf("  warning: %s\n", w.c_str());
            for (auto& L : set.levels) std::printf("%4d  %-4s  %4ds  %-28s  %zu hint line(s)\n", L.number, L.password.c_str(), L.timeLimit, L.title.c_str(), L.hint.size());
            return 0;
        }
        if (cmd == "verify" && argc >= 5) {
            TwsFile tws = loadTws(argv[3]);
            std::map<int, std::pair<std::string, long>> oracle;
            std::ifstream of(argv[4]); std::string line;
            while (std::getline(of, line)) {
                if (line.empty() || line[0] == '#') continue;
                std::istringstream ss(line); int lv, tt; std::string o, tk; ss >> lv >> tt >> o >> tk;
                oracle[lv] = {o, tk.empty() ? -1 : std::stol(tk)};
            }
            int pass = 0, total = 0, flagged = 0, flaggedOk = 0;
            for (auto& sol : tws.solutions) {
                const LevelData* L = set.find(sol.level);
                if (!L || !oracle.count(sol.level)) continue;
                ++total;
                Globals g; g.tick = 0x05; applyLinkInit(g); if (tws.ruleset == 1) g.randomForce = twsSlideToR(sol.slide);
                Game game(*L, g);
                std::map<uint32_t, uint8_t> in;
                for (auto& m : sol.moves) in[m.tick] |= twsDirToMask(m.dir);
                uint32_t end = sol.moves.empty() ? 0 : sol.moves.back().tick + 400;
                std::string o = "stall"; long at = -1;
                for (uint32_t t = 0; t < end; ++t) {
                    Input i; auto it = in.find(t); if (it != in.end()) i.dirs = it->second; i.ab = (t == 0);   // Tile World starts the level at tick 0, moved or not
                    game.tick(i);
                    std::string r = outcomeOf(game, t, &at); if (!r.empty()) { o = r; break; }
                }
                bool ok = oracle[sol.level].first == o && oracle[sol.level].second == at;
                pass += ok;
                if (game.outOfSync()) { ++flagged; flaggedOk += ok; std::printf("level %d: desync notice shown (%s)\n", sol.level, ok ? "still matches" : "differs"); }
                if (!ok) std::printf("level %d: got %s @%ld expected %s @%ld\n", sol.level, o.c_str(), at, oracle[sol.level].first.c_str(), oracle[sol.level].second);
            }
            std::printf("verify: %d/%d replays match (desync notice in %d, of which %d still match)\n", pass, total, flagged, flaggedOk);
            return pass == total ? 0 : 1;
        }
        if (cmd == "replay" && argc >= 4) {      // print the outcome of every solution (TSV, oracle format)
            TwsFile tws = loadTws(argv[3]);
            for (auto& sol : tws.solutions) {
                const LevelData* L = set.find(sol.level);
                if (!L || L->endMarker || sol.moves.empty()) continue;
                Globals g; g.tick = 0x05; applyLinkInit(g); if (tws.ruleset == 1) g.randomForce = twsSlideToR(sol.slide);
                Game game(*L, g);
                std::map<uint32_t, uint8_t> in;
                for (auto& m : sol.moves) in[m.tick] |= twsDirToMask(m.dir);
                uint32_t end = sol.moves.back().tick + 400;
                std::string o = "stall"; long at = -1;
                for (uint32_t t = 0; t < end; ++t) {
                    Input i; auto it = in.find(t); if (it != in.end()) i.dirs = it->second; i.ab = (t == 0);   // Tile World starts the level at tick 0, moved or not
                    game.tick(i);
                    std::string r = outcomeOf(game, t, &at); if (!r.empty()) { o = r; break; }
                }
                std::printf("%d\t%u\t%s\t%s\n", sol.level, sol.moves.back().tick + 1, o.c_str(), at < 0 ? "" : std::to_string(at).c_str());
            }
            return 0;
        }
        if (cmd == "map" && argc >= 4) {          // tile codes around a cell: map set.dat level col row
            const LevelData* L = set.find(std::stoi(argv[3]));
            int cx = std::stoi(argv[4]), cy = std::stoi(argv[5]);
            for (int y = cy - 3; y <= cy + 3; ++y) { for (int x = cx - 4; x <= cx + 4; ++x)
                std::printf(" %02X", (x < 0 || y < 0 || x > 31 || y > 31) ? 0xEE : L->map[y * 32 + x]); std::printf("\n"); }
            for (size_t i = 0; i < L->state.size(); ++i) if (L->state[i]) { int x = L->x[i] / 8, y = L->y[i] / 8;
                if (std::abs(x - cx) <= 4 && std::abs(y - cy) <= 3) std::printf("  obj slot %zu state %02X at (%d,%d)\n", i, L->state[i], x, y); }
            return 0;
        }
        if (cmd == "dump") {                      // objects after loading: slot type dir col row
            static const char* names[] = {"none", "chip", "bug", "paramecium", "fireball", "glider", "ball", "block",
                                          "tank", "walker", "blob", "teeth", "?", "?", "?", "?"};
            for (auto& L : set.levels) {
                std::printf("level %d\n", L.number);
                for (size_t i = 0; i < L.state.size(); ++i)
                    if (L.state[i]) std::printf("  slot %3zu %-10s %c%s (%d,%d)\n", i, names[(L.state[i] >> 2) & 15], "NESW"[L.state[i] & 3],
                                                (L.state[i] & 0x80) ? " moving" : "", L.x[i] / 8, L.y[i] / 8);
            }
            return 0;
        }
        if (cmd == "trace" && argc >= 5) {     // per-tick Chip cell for one solution: tick col row chips
            TwsFile tws = loadTws(argv[3]);
            int lv = std::stoi(argv[4]);
            for (auto& sol : tws.solutions) {
                if (sol.level != lv) continue;
                const LevelData* L = set.find(lv);
                if (!L) return 1;
                Globals g; g.tick = 0x05; applyLinkInit(g); if (tws.ruleset == 1) g.randomForce = twsSlideToR(sol.slide);
                Game game(*L, g);
                std::map<uint32_t, uint8_t> in;
                for (auto& m : sol.moves) in[m.tick] |= twsDirToMask(m.dir);
                uint32_t end = sol.moves.back().tick + 400;
                for (uint32_t t = 0; t < end; ++t) {
                    Input i; auto it = in.find(t); if (it != in.end()) i.dirs = it->second; i.ab = (t == 0);   // Tile World starts the level at tick 0, moved or not
                    game.tick(i);
                    std::printf("T %u %d %d chips=%d\n", t, game.objX(0) / 8, game.objY(0) / 8, game.chipsLeft());
                    if (game.finished() || game.dead()) break;
                }
            }
            return 0;
        }
        if (cmd == "snap" && argc >= 6) {      // full state after tick T: snap set.dat sol.tws level T
            TwsFile tws = loadTws(argv[3]);
            int lv = std::stoi(argv[4]); long upto = std::stol(argv[5]);
            for (auto& sol : tws.solutions) {
                if (sol.level != lv) continue;
                Globals g; g.tick = 0x05; applyLinkInit(g); if (tws.ruleset == 1) g.randomForce = twsSlideToR(sol.slide);
                Game game(*set.find(lv), g);
                std::map<uint32_t, uint8_t> in;
                for (auto& m : sol.moves) in[m.tick] |= twsDirToMask(m.dir);
                for (long t = 0; t <= upto; ++t) {
                    Input i; auto it = in.find(static_cast<uint32_t>(t)); if (it != in.end()) i.dirs = it->second; i.ab = (t == 0);
                    game.tick(i);
                }
                std::printf("map");
                for (int c = 0; c < kMapCells; ++c) { Cell v = game.cell(c); std::printf(" %d", isObj(v) ? 0x80 | (objOf(v) & 0x7F) : v); }
                std::printf("\nstate"); for (int k = 0; k < 128; ++k) std::printf(" %d", game.objState(k));
                std::printf("\nx"); for (int k = 0; k < 128; ++k) std::printf(" %d", game.objX(k));
                std::printf("\ny"); for (int k = 0; k < 128; ++k) std::printf(" %d", game.objY(k));
                std::printf("\nunder"); for (int k = 0; k < 128; ++k) std::printf(" %d", game.objUnderRaw(k));
                std::printf("\nstatus %s\n", game.dead() ? "dead" : game.finished() ? "won" : "running");
            }
            return 0;
        }
        if (cmd == "lynx" && argc >= 4) {        // cartridge-format level files, for testing against the original
            int n = 0;
            for (auto& L : set.levels) {
                Bytes f = buildLevelFile(L);
                std::ofstream o(std::string(argv[3]) + "/" + std::to_string(L.number) + ".bin", std::ios::binary);
                o.write(reinterpret_cast<const char*>(f.data()), static_cast<std::streamsize>(f.size()));
                ++n;
            }
            std::printf("wrote %d level files to %s\n", n, argv[3]);
            return 0;
        }
        if (cmd == "links") {                     // DAT trap/cloner wiring vs the Lynx reading-order rule
            int differ = 0;
            for (auto& L : set.levels) {
                if (!L.explicitLinks) continue;
                for (int c = 0; c < kMapCells; ++c) {
                    uint8_t v = L.map[c];
                    if (v != tile::BrownButton && v != tile::RedButton) continue;
                    uint8_t target = v == tile::BrownButton ? tile::Trap : tile::Cloner;
                    int pos = -1, ex = -1;
                    for (int k = 1; k <= kMapCells; ++k) { int q = (c + k) % kMapCells; if (L.map[q] == target) { pos = q; break; } }
                    for (auto& l : L.links) if (l.from == c) ex = l.to;
                    if (pos != ex) {
                        ++differ;
                        std::printf("level %3d %-24s %s button (%d,%d): DAT -> %s, reading order -> %s\n", L.number, L.title.c_str(),
                                    v == tile::BrownButton ? "brown" : "red", c % 32, c / 32,
                                    ex < 0 ? "none" : ("(" + std::to_string(ex % 32) + "," + std::to_string(ex / 32) + ")").c_str(),
                                    pos < 0 ? "none" : ("(" + std::to_string(pos % 32) + "," + std::to_string(pos / 32) + ")").c_str());
                    }
                }
            }
            std::printf("links: %d button(s) wired differently from the Lynx rule\n", differ);
            return 0;
        }
        if (cmd == "check" && argc >= 4) {
            std::ifstream mf(argv[3]); std::string line; int pass = 0, total = 0;
            while (std::getline(mf, line)) {
                auto colon = line.find(':');
                if (line.empty() || line[0] == '#' || colon == std::string::npos) continue;
                int n = std::stoi(line.substr(0, colon));
                const LevelData* L = set.find(n);
                if (!L) { std::printf("level %d: missing\n", n); ++total; continue; }
                long ticks; std::string r = playScript(*L, line.substr(colon + 1), &ticks);
                ++total; pass += r == "win";
                std::printf("level %2d %-24s %-6s after %ld ticks (%.1f s of %d s)\n", n, L->title.c_str(), r.c_str(), ticks, ticks / 20.0, L->timeLimit);
            }
            std::printf("check: %d/%d levels solved\n", pass, total);
            return pass == total ? 0 : 1;
        }
    } catch (const std::exception& e) { std::fprintf(stderr, "error: %s\n", e.what()); return 1; }
    std::fprintf(stderr, "bad arguments\n");
    return 2;
}
