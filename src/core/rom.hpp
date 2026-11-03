// ROM access: LNX container, cartridge directory, BPE decompression (spec doc 01).
#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace cc {

using Bytes = std::vector<uint8_t>;

struct DirEntry {
    uint32_t start = 0;   // cart offset
    uint16_t load = 0;    // non-zero => stored raw
    uint16_t size = 0;    // stored size
};

class Rom {
public:
    static constexpr int kFileCount = 172;
    static constexpr int kBodySize = 131072;

    // Loads an .lnx (with or without the 64-byte header). Throws std::runtime_error on failure.
    explicit Rom(const std::string& path);
    explicit Rom(Bytes body);

    const Bytes& body() const { return body_; }
    uint32_t bodyCrc32() const;
    const DirEntry& entry(int n) const { return dir_.at(n); }
    // Returns decoded file n (cached).
    const Bytes& file(int n) const;

    // Level slot N (1..150) is file 21+N.
    const Bytes& levelFile(int levelNumber) const { return file(21 + levelNumber); }

private:
    void readDirectory();
    Bytes body_;
    std::vector<DirEntry> dir_;
    mutable std::vector<Bytes> cache_;
    mutable std::vector<bool> cached_;
};

// BPE decoder (doc 01 §6). Returns decoded bytes; `consumed` receives the stream length.
Bytes bpeDecode(const Bytes& src, size_t pos, size_t* consumed);

uint32_t crc32(const uint8_t* data, size_t len);

} // namespace cc
