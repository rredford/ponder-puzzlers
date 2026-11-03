#include "tws.hpp"
#include "engine.hpp"
#include <fstream>
#include <iterator>
#include <stdexcept>

namespace cc {

static uint32_t le(const std::vector<uint8_t>& d, size_t p, int n) {
    uint32_t v = 0;
    for (int i = 0; i < n; ++i) v |= static_cast<uint32_t>(d.at(p + i)) << (8 * i);
    return v;
}

TwsFile loadTws(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("cannot open " + path);
    std::vector<uint8_t> d((std::istreambuf_iterator<char>(f)), {});
    if (d.size() < 8 || le(d, 0, 4) != 0x999B3335u) throw std::runtime_error("not a TWS file");
    TwsFile out;
    out.ruleset = d[4];
    size_t p = 8 + d[7];
    bool first = true;
    while (p + 4 <= d.size()) {
        uint32_t n = le(d, p, 4); p += 4;
        if (n == 0xFFFFFFFFu) break;
        if (n == 0) continue;
        if (p + n > d.size()) throw std::runtime_error("truncated TWS record");
        std::vector<uint8_t> r(d.begin() + p, d.begin() + p + n); p += n;
        bool allZero = n >= 6 && r[0] == 0 && r[1] == 0 && r[2] == 0 && r[3] == 0 && r[4] == 0 && r[5] == 0;
        if (first && allZero) {
            for (size_t i = 16; i < r.size() && r[i]; ++i) out.setName += static_cast<char>(r[i]);
            first = false;
            continue;
        }
        first = false;
        if (n < 16) continue;                 // password-only record
        TwsSolution s;
        s.level = static_cast<int>(le(r, 0, 2));
        s.password.assign(r.begin() + 2, r.begin() + 6);
        s.totalTicks = le(r, 12, 4);
        s.slide = r[7] & 7;
        uint32_t t = 0; bool firstMove = true;
        auto add = [&](uint16_t dir, uint32_t tf) {
            t = firstMove ? tf : t + tf + 1;
            firstMove = false;
            s.moves.push_back({t, dir});
        };
        size_t q = 16;
        while (q < r.size()) {
            uint8_t b = r[q];
            if ((b & 3) == 0) {
                for (int k = 0; k < 3; ++k) add((b >> (2 + 2 * k)) & 3, 3);
                q += 1;
            } else if ((b & 3) == 1) {
                add((b >> 2) & 7, b >> 5); q += 1;
            } else if ((b & 3) == 2) {
                uint32_t v = le(r, q, 2); add((v >> 2) & 7, v >> 5); q += 2;
            } else if (!(b & 0x10)) {
                uint32_t v = le(r, q, 4); add((v >> 2) & 3, (v >> 5) & 0x7FFFF); q += 4;   // top byte is not time (MS solutions set it)
            } else {
                int nb = ((b >> 2) & 3) + 2;
                uint64_t v = 0;
                for (int i = 0; i < nb; ++i) v |= static_cast<uint64_t>(r.at(q + i)) << (8 * i);
                add(static_cast<uint16_t>((v >> 5) & 0x1FF), static_cast<uint32_t>(v >> 14));
                q += nb;
            }
        }
        out.solutions.push_back(std::move(s));
    }
    return out;
}

uint8_t twsDirToMask(uint16_t d) {
    switch (d) {
        case 0: return kN; case 1: return kW; case 2: return kS; case 3: return kE;
        case 4: return kN | kW; case 5: return kS | kW; case 6: return kN | kE; case 7: return kS | kE;
        default: return 0;
    }
}

} // namespace cc
