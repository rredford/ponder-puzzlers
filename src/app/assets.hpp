#pragma once
#include <SDL.h>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

struct Sprite { int x = 0, y = 0; bool valid = false; };

class Assets {
public:
    bool load(SDL_Renderer* r, const std::string& dir);
    void draw(SDL_Renderer* r, std::string_view name, int x, int y, int size, Uint8 alpha = 255) const;
    void draw(SDL_Renderer* r, const Sprite& s, int x, int y, int size, Uint8 alpha = 255) const;
    Sprite get(std::string_view name) const;
    int cell() const { return cell_; }

    struct Font {
        SDL_Texture* tex = nullptr;
        int cw = 0, ch = 0;
        std::vector<int> widths;
    };
    const Font& font(bool large) const { return large ? large_ : small_; }
    ~Assets();

private:
    SDL_Texture* atlas_ = nullptr;
    int cell_ = 48;
    std::unordered_map<std::string, Sprite> map_;
    Font small_, large_;
};
