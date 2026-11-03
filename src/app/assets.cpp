#include "assets.hpp"
#include "atlas_index.hpp"
#include <cstdio>
#include <fstream>
#include <iterator>

static SDL_Texture* loadRgba(SDL_Renderer* r, const std::string& path, int headerWords,
                             std::vector<uint32_t>* header, std::vector<uint8_t>* extra, int extraBytes) {
    std::ifstream f(path, std::ios::binary);
    if (!f) { std::fprintf(stderr, "missing asset %s\n", path.c_str()); return nullptr; }
    std::vector<uint8_t> d((std::istreambuf_iterator<char>(f)), {});
    auto u32 = [&](size_t p) { return d[p] | (d[p + 1] << 8) | (d[p + 2] << 16) | (uint32_t(d[p + 3]) << 24); };
    header->clear();
    for (int i = 0; i < headerWords; ++i) header->push_back(u32(4 * i));
    size_t off = 4 * headerWords;
    if (extra) { extra->assign(d.begin() + off, d.begin() + off + extraBytes); off += extraBytes; }
    int w = (*header)[0], h = (*header)[1];
    if (d.size() < off + size_t(w) * h * 4) return nullptr;
    SDL_Texture* t = SDL_CreateTexture(r, SDL_PIXELFORMAT_ABGR8888, SDL_TEXTUREACCESS_STATIC, w, h);
    SDL_UpdateTexture(t, nullptr, d.data() + off, w * 4);
    SDL_SetTextureBlendMode(t, SDL_BLENDMODE_BLEND);
    return t;
}

bool Assets::load(SDL_Renderer* r, const std::string& dir) {
    std::vector<uint32_t> hdr;
    atlas_ = loadRgba(r, dir + "/atlas.rgba", 2, &hdr, nullptr, 0);
    if (!atlas_) return false;
    cell_ = kAtlasCell;
    for (const auto& e : kAtlas) map_[std::string(e.name)] = Sprite{e.x, e.y, true};
    for (int k = 0; k < 2; ++k) {
        Font& fo = k ? large_ : small_;
        std::vector<uint8_t> widths;
        fo.tex = loadRgba(r, dir + (k ? "/font_large.rgba" : "/font_small.rgba"), 4, &hdr, &widths, 95);
        if (!fo.tex) return false;
        fo.cw = hdr[2]; fo.ch = hdr[3];
        fo.widths.assign(widths.begin(), widths.end());
    }
    return true;
}

Assets::~Assets() {
    if (atlas_) SDL_DestroyTexture(atlas_);
    if (small_.tex) SDL_DestroyTexture(small_.tex);
    if (large_.tex) SDL_DestroyTexture(large_.tex);
}

Sprite Assets::get(std::string_view name) const {
    auto it = map_.find(std::string(name));
    return it == map_.end() ? Sprite{} : it->second;
}

void Assets::draw(SDL_Renderer* r, const Sprite& s, int x, int y, int size, Uint8 alpha) const {
    if (!s.valid) return;
    SDL_Rect src{s.x, s.y, cell_, cell_}, dst{x, y, size, size};
    SDL_SetTextureAlphaMod(atlas_, alpha);
    SDL_RenderCopy(r, atlas_, &src, &dst);
}

void Assets::draw(SDL_Renderer* r, std::string_view name, int x, int y, int size, Uint8 alpha) const {
    draw(r, get(name), x, y, size, alpha);
}
