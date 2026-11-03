#include "ui.hpp"

namespace ui {

int textWidth(const Assets& a, bool large, const std::string& s) {
    const auto& f = a.font(large);
    int w = 0;
    for (unsigned char ch : s) if (ch >= 32 && ch < 127) w += f.widths[ch - 32];
    return w;
}

static void raw(SDL_Renderer* r, const Assets::Font& f, const std::string& s, int x, int y, SDL_Color c) {
    SDL_SetTextureColorMod(f.tex, c.r, c.g, c.b);
    SDL_SetTextureAlphaMod(f.tex, c.a);
    for (unsigned char ch : s) {
        if (ch < 32 || ch >= 127) continue;
        int i = ch - 32;
        SDL_Rect src{(i % 16) * f.cw, (i / 16) * f.ch, f.cw, f.ch};
        SDL_Rect dst{x - 2, y - 2, f.cw, f.ch};
        SDL_RenderCopy(r, f.tex, &src, &dst);
        x += f.widths[i];
    }
}

void text(SDL_Renderer* r, const Assets& a, bool large, const std::string& s, int x, int y,
          SDL_Color c, Align al, bool outline) {
    const auto& f = a.font(large);
    int w = textWidth(a, large, s);
    if (al == Center) x -= w / 2;
    else if (al == Right) x -= w;
    if (outline) {
        SDL_Color o{20, 18, 34, c.a};
        for (int dy = -2; dy <= 2; ++dy)
            for (int dx = -2; dx <= 2; ++dx)
                if (dx * dx + dy * dy <= 5 && (dx || dy)) raw(r, f, s, x + dx, y + dy, o);
    }
    raw(r, f, s, x, y, c);
}

void panel(SDL_Renderer* r, SDL_Rect box, SDL_Color fill, SDL_Color border) {
    SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_BLEND);
    SDL_SetRenderDrawColor(r, fill.r, fill.g, fill.b, fill.a);
    SDL_RenderFillRect(r, &box);
    SDL_SetRenderDrawColor(r, border.r, border.g, border.b, border.a);
    for (int k = 0; k < 3; ++k) {
        SDL_Rect b{box.x + k, box.y + k, box.w - 2 * k, box.h - 2 * k};
        SDL_RenderDrawRect(r, &b);
    }
}

} // namespace ui
