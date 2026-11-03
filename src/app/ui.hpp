#pragma once
#include <SDL.h>
#include <string>
#include "assets.hpp"

namespace ui {
enum Align { Left, Center, Right };
int textWidth(const Assets& a, bool large, const std::string& s);
void text(SDL_Renderer* r, const Assets& a, bool large, const std::string& s, int x, int y,
          SDL_Color c, Align al = Left, bool outline = true);
void panel(SDL_Renderer* r, SDL_Rect box, SDL_Color fill, SDL_Color border);
} // namespace ui
