#include <algorithm>
#include "level.hpp"
#include <stdexcept>

namespace cc {

char charsetToAscii(uint8_t c) {
    if (c == 0x01) return ' ';
    if (c >= 0x02 && c <= 0x0B) return static_cast<char>('0' + (c - 0x02));
    if (c >= 0x0C && c <= 0x25) return static_cast<char>('A' + (c - 0x0C));
    switch (c) {
        case 0x26: return '!'; case 0x27: return '"'; case 0x28: return '\'';
        case 0x29: return '('; case 0x2A: return ')'; case 0x2B: return ',';
        case 0x2C: return '-'; case 0x2D: return '.'; case 0x2E: return ':';
        case 0x2F: return ';'; case 0x30: return '?'; case 0x31: return '#';
        default: return '?';
    }
}

uint8_t asciiToCharset(char ch) {
    unsigned char c = static_cast<unsigned char>(ch);
    if (c >= 'a' && c <= 'z') c = static_cast<unsigned char>(c - 'a' + 'A');
    if (c == ' ') return 0x01;
    if (c >= '0' && c <= '9') return static_cast<uint8_t>(0x02 + (c - '0'));
    if (c >= 'A' && c <= 'Z') return static_cast<uint8_t>(0x0C + (c - 'A'));
    static const char punct[] = "!\"'(),-.:;?#";
    for (int k = 0; punct[k]; ++k) if (punct[k] == c) return static_cast<uint8_t>(0x26 + k);
    return 0x01;                                   // anything else shows as a space
}

Bytes buildLevelFile(const LevelData& L) {
    if (L.endMarker) return Bytes{0xFF};
    Bytes f(0x582, 0);
    for (int i = 0; i < kMapCells; ++i) f[i] = L.map[i];
    for (int i = 0; i < kSlots && i < static_cast<int>(L.state.size()); ++i) { f[0x400 + i] = L.state[i]; f[0x480 + i] = L.x[i]; f[0x500 + i] = L.y[i]; }
    f[0x580] = static_cast<uint8_t>(L.timeLimit & 0xFF); f[0x581] = static_cast<uint8_t>((L.timeLimit >> 8) & 0xFF);
    size_t budget = 126;
    auto put = [&](const std::string& s) -> bool {
        if (budget < 2) return false;
        size_t n = std::min(s.size(), budget - 2);       // keep room for this line's 0 and the list's final 0
        for (size_t k = 0; k < n; ++k) f.push_back(asciiToCharset(s[k]));
        f.push_back(0); budget -= n + 1;
        return n == s.size();
    };
    put(L.title.substr(0, kMaxTitleChars));
    // The cartridge's hint box holds lines of at most 19 characters (longer lines crash the original), and
    // the real levels never use more than 7 lines: re-wrap the hint to fit.
    std::vector<std::string> lines;
    {
        std::string cur, word, all;
        for (const auto& h : L.hint) { if (!all.empty()) all += ' '; all += h; }
        auto flush = [&]() {
            while (word.size() > kHintLineChars) { if (!cur.empty()) { lines.push_back(cur); cur.clear(); }
                                                   lines.push_back(word.substr(0, kHintLineChars)); word.erase(0, kHintLineChars); }
            if (word.empty()) return;
            if (!cur.empty() && cur.size() + 1 + word.size() > kHintLineChars) { lines.push_back(cur); cur.clear(); }
            cur += (cur.empty() ? "" : " ") + word; word.clear();
        };
        for (char ch : all) { if (ch == ' ' || ch == '\n') flush(); else word += ch; }
        flush();
        if (!cur.empty()) lines.push_back(cur);
        if (lines.size() > kHintLines) lines.resize(kHintLines);
    }
    for (const auto& h : lines) if (!put(h)) break;
    if (!lines.empty()) f.push_back(0);           // hint list terminator (files without hints just end)
    return f;
}

std::string decodeText(const uint8_t* p, size_t n) {
    std::string s;
    for (size_t i = 0; i < n; ++i) s += charsetToAscii(p[i]);
    return s;
}

LevelData parseLevel(const Bytes& f, int number) {
    LevelData L;
    L.number = number;
    if (f.size() == 1 && f[0] == 0xFF) { L.endMarker = true; return L; }
    if (f.size() < 0x583) throw std::runtime_error("level file too short");
    for (int i = 0; i < kMapCells; ++i) L.map[i] = f[i];
    for (int i = 0; i < kSlots; ++i) {
        L.state[i] = f[0x400 + i]; L.x[i] = f[0x480 + i]; L.y[i] = f[0x500 + i];
    }
    L.timeLimit = f[0x580] | (f[0x581] << 8);
    size_t p = 0x582;
    auto line = [&](std::string& out) -> bool {
        size_t s = p;
        while (p < f.size() && f[p] != 0) ++p;
        out = decodeText(&f[s], p - s);
        bool terminated = p < f.size();
        if (terminated) ++p;  // skip 00
        return terminated || p > s;
    };
    line(L.title);
    while (p < f.size()) {
        std::string h;
        size_t before = p;
        line(h);
        if (h.empty()) break;           // empty line ends the hint
        L.hint.push_back(h);
        if (p == before) break;
    }
    return L;
}

uint8_t Rng::next() {
    int a = lo >> 1;
    int c = a & 1;
    a >>= 1;
    int r = a - lo - (1 - c);
    a = r & 0xFF;
    c = a & 1;
    int c2 = hi >> 7;
    hi = static_cast<uint8_t>(((hi << 1) | c) & 0xFF);
    lo = static_cast<uint8_t>((lo >> 1) | (c2 << 7));
    return static_cast<uint8_t>(lo ^ hi);
}

std::vector<std::string> generatePasswords() {
    Rng g;
    auto letter = [&]() -> char {
        for (;;) {
            int r = g.next() & 0x1F;
            if (r < 26) return static_cast<char>('A' + r);
        }
    };
    std::vector<std::string> slots(256, std::string(4, ' '));
    auto fill = [&](int s) { for (int k = 0; k < 4; ++k) slots[s][k] = letter(); };
    fill(0);
    for (int s = 255; s >= 1; --s) fill(s);
    for (int s : {97, 106, 113}) slots[s][0] = letter();
    slots.resize(kLevelSlots);
    return slots;
}

} // namespace cc
