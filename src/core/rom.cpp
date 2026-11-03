#include "rom.hpp"
#include <fstream>
#include <stdexcept>
#include <iterator>

namespace cc {

uint32_t crc32(const uint8_t* d, size_t n) {
    static uint32_t table[256];
    static bool init = false;
    if (!init) {
        for (uint32_t i = 0; i < 256; ++i) {
            uint32_t c = i;
            for (int k = 0; k < 8; ++k) c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
            table[i] = c;
        }
        init = true;
    }
    uint32_t c = 0xFFFFFFFFu;
    for (size_t i = 0; i < n; ++i) c = table[(c ^ d[i]) & 0xFF] ^ (c >> 8);
    return c ^ 0xFFFFFFFFu;
}

static Bytes readAll(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("cannot open ROM file: " + path);
    return Bytes(std::istreambuf_iterator<char>(f), {});
}

Rom::Rom(const std::string& path) : Rom(readAll(path)) {}

Rom::Rom(Bytes data) {
    if (data.size() >= 4 && data[0] == 'L' && data[1] == 'Y' && data[2] == 'N' && data[3] == 'X')
        data.erase(data.begin(), data.begin() + 64);
    if (data.size() != kBodySize)
        throw std::runtime_error("unexpected cartridge size (expected 128 KiB body)");
    body_ = std::move(data);
    readDirectory();
    cache_.resize(kFileCount);
    cached_.assign(kFileCount, false);
}

uint32_t Rom::bodyCrc32() const { return crc32(body_.data(), body_.size()); }

void Rom::readDirectory() {
    dir_.resize(kFileCount);
    for (int n = 0; n < kFileCount; ++n) {
        const uint8_t* e = &body_[0x200 + 8 * n];
        DirEntry d;
        d.start = e[0] * 512u + (e[1] | (e[2] << 8));
        d.load = static_cast<uint16_t>(e[4] | (e[5] << 8));
        d.size = static_cast<uint16_t>(e[6] | (e[7] << 8));
        if (d.start + d.size > body_.size()) throw std::runtime_error("bad directory entry");
        dir_[n] = d;
    }
}

const Bytes& Rom::file(int n) const {
    if (n < 0 || n >= kFileCount) throw std::out_of_range("file index");
    if (!cached_[n]) {
        const DirEntry& d = dir_[n];
        if (d.load) {
            cache_[n] = Bytes(body_.begin() + d.start, body_.begin() + d.start + d.size);
        } else {
            size_t used = 0;
            cache_[n] = bpeDecode(body_, d.start, &used);
            if (used != d.size) throw std::runtime_error("compressed file length mismatch");
        }
        cached_[n] = true;
    }
    return cache_[n];
}

Bytes bpeDecode(const Bytes& src, size_t pos, size_t* consumed) {
    Bytes out;
    const size_t start = pos;
    auto at = [&](size_t p) -> uint8_t {
        if (p >= src.size()) throw std::runtime_error("BPE stream overrun");
        return src[p];
    };
    for (;;) {
        const int n = at(pos);
        const int more = at(pos + 1);
        const int count = at(pos + 2) | (at(pos + 3) << 8);
        pos += 4;
        uint8_t sym[256], left[256], right[256];
        for (int i = 1; i <= n; ++i) {
            sym[i] = at(pos); left[i] = at(pos + 1); right[i] = at(pos + 2);
            pos += 3;
        }
        // For speed: for every byte value, list of entries in increasing order.
        struct Frame { uint8_t b; int limit; };
        std::vector<Frame> stack;
        for (int k = 0; k < count; ++k) {
            stack.push_back({at(pos++), n + 1});
            while (!stack.empty()) {
                Frame f = stack.back(); stack.pop_back();
                int e = 0;
                for (int i = f.limit - 1; i >= 1; --i) if (sym[i] == f.b) { e = i; break; }
                if (!e) { out.push_back(f.b); continue; }
                stack.push_back({right[e], e});
                stack.push_back({left[e], e});
            }
        }
        if (!more) break;
    }
    if (consumed) *consumed = pos - start;
    return out;
}

} // namespace cc
