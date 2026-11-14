// Ponder Puzzlers — SDL2 front-end. Engine rules: spec docs 03–05; presentation: doc 06 (with new art).
#include <SDL.h>
#include <cstdio>
#include <cctype>
#include <csignal>
#include <fcntl.h>
#include <sys/wait.h>
#include <unistd.h>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <algorithm>
#include <array>
#include <cmath>
#include <memory>
#include <string>
#include <vector>
#include "assets.hpp"
#include "core/engine.hpp"
#include "core/dat.hpp"
#include "core/rom.hpp"
#include "builtin_levels.hpp"
#include "core/tws.hpp"
#include "ui.hpp"
#include "audio/synth.hpp"

unsigned long windowX11Id(SDL_Window* w);   // wm.cpp (kept apart: the X11 headers define names that clash)

using namespace cc;

namespace {

constexpr int kTile = 48;
SDL_Rect modeBox(int k) { return SDL_Rect{180, 210 + k * 28, 20, 20}; }
constexpr int kView = 9;                       // visible tiles per axis
constexpr int kViewPx = kTile * kView;         // 432
constexpr int kPanelW = 208;
constexpr int kScreenW = kViewPx + kPanelW, kScreenH = kViewPx;   // game area
constexpr int kMenuH = 26;                     // menu bar above the game area
constexpr int kWinH = kScreenH + kMenuH;
constexpr double kTickSeconds = 3.0 / 59.9;    // doc 05 §1

const SDL_Color kWhite{255, 255, 255, 255}, kYellow{255, 214, 64, 255}, kCyan{120, 230, 255, 255},
                kRed{255, 110, 100, 255}, kGreen{120, 240, 150, 255}, kGrey{170, 176, 196, 255};

enum class Screen { Title, Password, Play, LevelDone, Died, Ending };

struct Options {
    std::string rom;               // cartridge image (optional)
    std::string levels;            // DAT level set (optional)
    std::string assets = ASSET_DIR;
    int level = 0;
    std::string shot;             // screenshot path (headless test)
    int shotTicks = 0;
    std::string replay;           // TWS file to auto-play
    std::string script;           // headless key script: FRAME:key,... (keys: up down left right space enter b backspace r)
    std::string hacks;            // headless: "step", "helmet" or "step,helmet" (not saved)
    int mode = -1;                // -1 = saved setting, 0 = strict Lynx ROM, 1 = extended Lynx mode
    std::string uiTest;           // headless: open a menu/dialog for the screenshot
    bool nativeDialogs = true;    // use zenity/kdialog file dialogs when available
    int scale = 2;
};

class App {
public:
    App(const Options& o) : opt_(o) {}
    int run();

private:
    // flow
    void startLevel(int number);
    void finishLevel();
    void onKey(SDL_Keycode k, bool down);
    void update();                 // one tick
    // drawing
    void render(double alpha);
    void drawPlayfield(double alpha);
    void drawHud();
    void drawOverlay();
    void drawDesync();
    void drawSoundNote();
    SDL_Rect desyncButton() const { return SDL_Rect{kViewPx - 24 - 34, 12 + 8, 26, 26}; }   // game-area coordinates
    bool desyncInfo_ = false;      // the explanation under the desync notice is open
    void drawTitle(double alpha);
    void drawPassword(double alpha);
    std::string tileSprite(uint8_t code) const;
    std::string objectSprite(int slot) const;
    void loadSet();                // (re)load the level set in the current rules mode
    void setExtended(bool on);
    void loadSettings();
    void saveSettings() const;
    static std::string settingsPath();
    // menus and dialogs (drawn over the whole window)
    enum class Modal { None, Menu, LevelDialog, Browser, Message, Waiting, Inventory, Moves };
    enum Cmd { CmdLoadRom, CmdLoadPack, CmdQuit, CmdSelectLevel, CmdToggleMusic, CmdToggleSfx, CmdToggleStep, CmdToggleHelmet, CmdInventory, CmdNextLevel, CmdPrevLevel, CmdShowMoves };
    struct MenuItem { const char* label; const char* keys; int cmd; };
    struct Menu { const char* title; std::vector<MenuItem> items; };
    std::vector<Menu> menus_ = {
        {"File", {{"Load ROM...", "Ctrl+Shift+O", CmdLoadRom}, {"Load Level Pack...", "Ctrl+O", CmdLoadPack},
                  {nullptr, nullptr, -1}, {"Quit", "Ctrl+Q", CmdQuit}}},
        {"Level", {{"Select Level...", "Ctrl+G", CmdSelectLevel}, {"Next Level", "Ctrl+N", CmdNextLevel}, {"Previous Level", "Ctrl+P", CmdPrevLevel}, {nullptr, nullptr, -1}, {"Show Moves...", "Ctrl+M", CmdShowMoves}}},
        {"Options", {{"Music", "", CmdToggleMusic}, {"Sound Effects", "", CmdToggleSfx}}},
        {"Hacks", {{"Step Mode", "", CmdToggleStep}, {"Helmet", "", CmdToggleHelmet}, {nullptr, nullptr, -1}, {"Edit Inventory...", "Ctrl+I", CmdInventory}}},
    };
    bool isToggle(int cmd) const { return cmd == CmdToggleMusic || cmd == CmdToggleSfx || cmd == CmdToggleStep || cmd == CmdToggleHelmet; }
    bool toggleOn(int cmd) const { return cmd == CmdToggleMusic ? musicOn_ : cmd == CmdToggleSfx ? sfxOn_ : cmd == CmdToggleStep ? stepMode_ : helmet_; }
    // Hacks (never part of the Lynx rules): step mode runs the game only on key presses, a whole move at a time,
    // with undo; the helmet makes Chip and monsters walls to each other.
    bool stepMode_ = false, helmet_ = false;
    enum StepKind { StepMove, StepTick, StepWait };
    struct StepAction { StepKind kind; uint8_t dir; };
    bool stepActive_ = false, stepQueued_ = false;
    bool heldSpace_ = false, heldB_ = false;   // step mode: a held key keeps stepping
    StepAction step_{StepTick, 0}, queued_{StepTick, 0};
    int stepDone_ = 0, stepX_ = 0, stepY_ = 0; bool stepMoved_ = false;
    struct Snapshot { std::unique_ptr<Game> game; Globals globals; int anim, attempts; std::vector<int> px, py; size_t moves; };
    // Step Mode records the steps of the attempt in Tile World's letters: U D L R a move, '-' a tick of waiting
    // (Space is one '-', B as many '-' as the ticks it ran); undo takes them back.
    std::string moves_;
    bool movesCopied_ = false;
    std::vector<Snapshot> undo_;
    static constexpr size_t kUndoMax = 5000;
    void queueStep(StepKind k, uint8_t dir);
    void beginStep();
    void undoStep();
    // Step mode plays Chip's death animation by itself, but only for a death the game has recorded, and for at most
    // 60 ticks: off-map writes can leave slot 0 in a dying-looking state that never ends (the game then simply
    // goes on, as it would without step mode).
    int autoTicks_ = 0;
    // Fake Chips (off-map glitches) can bring a dead Chip straight back to life: the death stays recorded but slot 0
    // is a walking Chip again, so the animation only counts while slot 0 is really dying (or has just vanished).
    bool chipDying() const {
        if (!game_ || game_->dead() || game_->finished() || autoTicks_ >= 60 || game_->deathReason() == DeathReason::None) return false;
        uint8_t s0 = game_->objState(0);
        return (s0 & 0x40) || s0 == 0;
    }
    // inventory editor (hack): rows 0-3 key counts (0-255), rows 4-7 boots on/off; applied on OK
    int inv_[8] = {}; int invRow_ = 0; bool invTyped_ = false; bool invEdited_ = false;
    void openInventory();
    void applyInventory();
    void invAdjust(int row, int delta);
    SDL_Rect invBox() const { return SDL_Rect{kScreenW / 2 - 190, kMenuH + 12, 380, 408}; }
    SDL_Rect invRowRect(int r) const { SDL_Rect b = invBox(); return SDL_Rect{b.x + 16, b.y + 52 + r * 37, b.w - 32, 34}; }
    void pushUndo();
    void clearSteps() { stepActive_ = stepQueued_ = false; undo_.clear(); }
    // audio: newly composed music and effects played by our own synthesizer (src/audio)
    audio::Synth synth_{48000};
    std::map<std::string, audio::Song> songs_;
    SDL_AudioDeviceID audioDev_ = 0;
    bool musicOn_ = true, sfxOn_ = true;
    const audio::Song* curMusic_ = nullptr;
    bool restartMusic_ = false;
    int loopHandle_ = 0; uint8_t loopId_ = 0;
    void initAudio();
    void updateAudio();
    const audio::Song* song(const std::string& name) const { auto it = songs_.find(name); return it == songs_.end() ? nullptr : &it->second; }
    std::string levelTrack() const;
    Modal modal_ = Modal::None;
    int menuOpen_ = -1, menuHover_ = -1;
    std::string levelInput_, dialogError_, message_;
    // in-app file browser
    struct Entry { std::string name; bool dir; };
    int browserPurpose_ = CmdLoadPack;
    std::string browserDir_;
    std::vector<Entry> entries_;
    int browserSel_ = 0, browserTop_ = 0;
    Uint32 lastClick_ = 0; int lastClickRow_ = -1;
    std::string lastDir_;
    bool quit_ = false;
    pid_t dialogPid_ = -1; int dialogFd_ = -1; std::string dialogOut_;   // native file dialog process
    bool startNativeDialog(int purpose, const std::string& startDir);
    void pollNativeDialog();
    void cancelNativeDialog();
    void runCommand(int cmd);
    bool onModalKey(SDL_Keycode k, Uint16 mod);
    void onMouse(const SDL_Event& e);
    void drawMenuBar();
    void drawModal();
    SDL_Rect menuTitleRect(int m) const;
    SDL_Rect menuItemRect(int m, int k) const;
    SDL_Rect dropRect(int m) const;
    std::string levelRanges() const;
    void acceptLevelDialog();
    void cycleLevel(int dir);
    void openFile(int purpose);
    void browseTo(const std::string& dir);
    void browserActivate();
    void loadRomFile(const std::string& path);
    void loadPackFile(const std::string& path);
    void showMessage(const std::string& m) { message_ = m; modal_ = Modal::Message; }
    void resetProgress();

    Options opt_;
    SDL_Window* win_ = nullptr;
    SDL_Renderer* ren_ = nullptr;
    Assets assets_;
    LevelSet set_;
    bool extended_ = false;        // rules mode: strict Lynx ROM / extended Lynx mode
    int strictAltered_ = 0;        // levels changed to fit the cartridge in strict mode
    std::string loadError_;
    std::vector<std::string> passwords_;   // index = level number - 1
    int maxLevel() const { return static_cast<int>(passwords_.size()); }
    Screen screen_ = Screen::Title;
    int level_ = 1;
    LevelData data_;
    Globals globals_;
    std::unique_ptr<Game> game_;
    uint8_t held_ = 0;             // currently held directions
    bool abPressed_ = false;
    bool paused_ = false;
    int anim_ = 0;                 // tile animation counter (runs every tick, doc 06 §5)
    int attempts_ = 0;
    long totalScore_ = 0;
    int skipCounter_ = 10, skipTimer_ = 0; bool skipOffer_ = false, skipYes_ = false;
    long timeBonus_ = 0, levelBonus_ = 0;
    std::string pw_ = "BDHP"; int pwCursor_ = 0;
    std::vector<int> prevX_, prevY_;
    // replay
    std::map<uint32_t, uint8_t> replayInput_;
    uint32_t replayTick_ = 0; bool replaying_ = false;
    std::vector<std::pair<int, std::string>> script_;  // (tick, action)
    int frameTicks_ = 0;
    long gameTicks_ = 0;           // test log only
};

// ---------------------------------------------------------------- sprites
std::string App::tileSprite(uint8_t c) const {
    char buf[32];
    switch (c) {
        case tile::ForceN: case tile::ForceE: case tile::ForceS: case tile::ForceW:
            std::snprintf(buf, sizeof buf, "force_%c_%d", "NESW"[c - tile::ForceN], anim_ & 3); return buf;
        case tile::ForceRandom: std::snprintf(buf, sizeof buf, "force_R_%d", (anim_ >> 1) & 3); return buf;
        case tile::Teleport: std::snprintf(buf, sizeof buf, "teleport_%d", (anim_ >> 1) % 3); return buf;
        case tile::Fire: std::snprintf(buf, sizeof buf, "fire_%d", (anim_ >> 1) % 3); return buf;
        case tile::Water: std::snprintf(buf, sizeof buf, "water_%d", (anim_ >> 1) % 3); return buf;
        case tile::Exit: std::snprintf(buf, sizeof buf, "exit_%d", (anim_ >> 1) % 3); return buf;
        case tile::ToggleOpen: case tile::ToggleClosed: {
            bool closed = (c == tile::ToggleClosed) != game_->togglesSwapped();
            std::snprintf(buf, sizeof buf, closed ? "toggleclosed_%d" : "toggleopen_%d", anim_ & 3); return buf;
        }
        default: std::snprintf(buf, sizeof buf, "tile_%02X", c); return buf;
    }
}

std::string App::objectSprite(int i) const {
    uint8_t st = game_->objState(i);
    char buf[32];
    if (st & 0x40) {
        int f = st & 0x3F;
        const char* kind = f < 6 ? "explode" : f < 12 ? "smoke" : "splash";
        std::snprintf(buf, sizeof buf, "fx_%s_%d", kind, f % 6); return buf;
    }
    int type = (st >> 2) & 15, d = st & 3;
    int frame = ((game_->objX(i) | game_->objY(i)) >> 1) & 3;
    if (type == T_CHIP) {
        if (game_->pushingPose() && i == 0) { std::snprintf(buf, sizeof buf, "heropush_%d", d); return buf; }
        std::snprintf(buf, sizeof buf, "hero_%d_%d", d, frame); return buf;
    }
    if (type == T_BLOCK) return "obj_7";
    std::snprintf(buf, sizeof buf, "obj_%d_%d_%d", type, d, frame); return buf;
}

// ---------------------------------------------------------------- flow
void App::startLevel(int n) {
    level_ = n;
    const LevelData* L = set_.find(n);
    // Finishing the last level of the main sequence (or running off the end) shows the ending.
    if (!L || L->endMarker) { screen_ = Screen::Ending; game_.reset(); return; }
    data_ = *L;
    game_ = std::make_unique<Game>(data_, globals_);
    game_->setHelmet(helmet_);
    clearSteps(); invEdited_ = false; autoTicks_ = 0; moves_.clear();
    prevX_.assign(game_->slots(), 0); prevY_.assign(game_->slots(), 0);
    for (int i = 0; i < game_->slots(); ++i) { prevX_[i] = game_->objX(i); prevY_[i] = game_->objY(i); }
    screen_ = Screen::Play; paused_ = false;
    restartMusic_ = true;
    skipTimer_ = 200;
    skipOffer_ = (level_ <= set_.mainCount - 5 && skipCounter_ == 0);   // never offered for the last 5 (cartridge: 139)
    skipYes_ = false;
}

void App::finishLevel() {
    // doc 05 §5
    timeBonus_ = game_->timeLeft() * 10L;
    static const int kFactor[6] = {0, 500, 400, 300, 200, 100};
    int a = attempts_ > 5 ? 5 : attempts_;
    levelBonus_ = std::max(500L, long(level_) * kFactor[a]);
    totalScore_ += timeBonus_ + levelBonus_;
    screen_ = Screen::LevelDone;
}

void App::onKey(SDL_Keycode k, bool down) {
    if (down) {
        Uint16 mod = SDL_GetModState();
        if (onModalKey(k, mod)) { held_ = 0; return; }
    } else if (modal_ != Modal::None) return;
    uint8_t bit = 0;
    switch (k) {
        case SDLK_UP: case SDLK_w: bit = kN; break;
        case SDLK_RIGHT: case SDLK_d: bit = kE; break;
        case SDLK_DOWN: case SDLK_s: bit = kS; break;
        case SDLK_LEFT: case SDLK_a: bit = cc::kW; break;
        default: break;
    }
    if (bit && !replaying_) { if (down) held_ |= bit; else held_ &= ~bit; }
    if (k == SDLK_SPACE) heldSpace_ = down;
    if (k == SDLK_b) heldB_ = down;
    if (!down) return;
    bool confirm = (k == SDLK_RETURN || k == SDLK_SPACE || k == SDLK_KP_ENTER);
    switch (screen_) {
    case Screen::Title:
        if (confirm) { screen_ = Screen::Password; pw_ = passwords_[level_ - 1]; pwCursor_ = 0; }
        else if (k == SDLK_UP || k == SDLK_w) setExtended(false);
        else if (k == SDLK_DOWN || k == SDLK_s) setExtended(true);
        else if (k == SDLK_m || k == SDLK_TAB || k == SDLK_LEFT || k == SDLK_RIGHT) setExtended(!extended_);
        break;
    case Screen::Password:
        if (k == SDLK_LEFT && pwCursor_ > 0) --pwCursor_;
        else if (k == SDLK_RIGHT && pwCursor_ < 3) ++pwCursor_;
        else if (k == SDLK_UP) pw_[pwCursor_] = pw_[pwCursor_] == 'Z' ? 'A' : pw_[pwCursor_] + 1;
        else if (k == SDLK_DOWN) pw_[pwCursor_] = pw_[pwCursor_] == 'A' ? 'Z' : pw_[pwCursor_] - 1;
        else if (k >= SDLK_a && k <= SDLK_z) { pw_[pwCursor_] = char('A' + (k - SDLK_a)); if (pwCursor_ < 3) ++pwCursor_; }
        else if (k == SDLK_ESCAPE) screen_ = Screen::Title;
        else if (confirm) {
            for (int i = 0; i < maxLevel(); ++i) if (passwords_[i] == pw_ && !set_.find(i + 1)->endMarker) { if (i + 1 != level_) attempts_ = 0; level_ = i + 1; break; }
            held_ = 0; startLevel(level_);
        }
        break;
    case Screen::Play:
        if (skipOffer_) {
            if (k == SDLK_LEFT) skipYes_ = true;
            else if (k == SDLK_RIGHT) skipYes_ = false;
            else if (confirm) {
                skipOffer_ = false; skipCounter_ = 10;
                if (skipYes_) { attempts_ = 0; startLevel(level_ + 1); }
            }
            held_ = 0;
            break;
        }
        if (stepMode_ && !replaying_ && !paused_) {
            if (bit) { queueStep(StepMove, bit); break; }
            if (k == SDLK_SPACE) { queueStep(StepTick, 0); break; }
            if (k == SDLK_b) { queueStep(StepWait, 0); break; }
            if (k == SDLK_BACKSPACE) { undoStep(); break; }
        }
        if (k == SDLK_p || k == SDLK_PAUSE) { if (!game_->waiting() || paused_) paused_ = !paused_; }
        else if (k == SDLK_r || k == SDLK_BACKSPACE) { held_ = 0; startLevel(level_); }
        else if (k == SDLK_ESCAPE) { screen_ = Screen::Title; held_ = 0; }
        else if (confirm) abPressed_ = true;
        break;
    case Screen::LevelDone:
        if (confirm) {
            attempts_ = 0; skipCounter_ = 10; held_ = 0;
            if (level_ == set_.mainCount) { screen_ = Screen::Ending; game_.reset(); }
            else startLevel(level_ + 1);
        }
        break;
    case Screen::Died:
        if (stepMode_ && k == SDLK_BACKSPACE && !undo_.empty()) { undoStep(); break; }
        if (confirm) { held_ = 0; startLevel(level_); }
        break;
    case Screen::Ending:
        if (confirm || k == SDLK_ESCAPE) { screen_ = Screen::Title; level_ = 1; totalScore_ = 0; attempts_ = 0; }
        break;
    }
}

void App::queueStep(StepKind k, uint8_t dir) {
    if (game_->dead() || game_->finished() || chipDying()) return;
    queued_ = StepAction{k, dir}; stepQueued_ = true;   // one action is buffered while the previous one plays out
}

void App::pushUndo() {
    Snapshot sn{std::make_unique<Game>(*game_), globals_, anim_, attempts_, prevX_, prevY_, moves_.size()};
    undo_.push_back(std::move(sn));
    if (undo_.size() > kUndoMax) undo_.erase(undo_.begin());
}

void App::openInventory() {
    if (!game_ || screen_ != Screen::Play) { showMessage("Start a level to edit the inventory."); return; }
    for (int k = 0; k < 4; ++k) inv_[k] = game_->key(k);
    inv_[4] = game_->skates(); inv_[5] = game_->suction(); inv_[6] = game_->fireBoots(); inv_[7] = game_->flippers();
    invRow_ = 0; invTyped_ = false;
    modal_ = Modal::Inventory;
}

void App::invAdjust(int row, int delta) {
    if (row >= 4) inv_[row] = !inv_[row];
    else inv_[row] = std::clamp(inv_[row] + delta, 0, 255);
    invTyped_ = false;
}

// The edit is one undo step in Step Mode.
void App::applyInventory() {
    modal_ = Modal::None;
    if (!game_) return;
    bool same = true;
    for (int k = 0; k < 4; ++k) same = same && inv_[k] == game_->key(k);
    same = same && bool(inv_[4]) == game_->skates() && bool(inv_[5]) == game_->suction() && bool(inv_[6]) == game_->fireBoots() && bool(inv_[7]) == game_->flippers();
    if (same) return;
    stepActive_ = stepQueued_ = false;
    pushUndo();
    for (int k = 0; k < 4; ++k) game_->setKey(k, static_cast<uint8_t>(inv_[k]));
    for (int b = 0; b < 4; ++b) game_->setBoots(b, inv_[4 + b] != 0);
    invEdited_ = true;
}

void App::beginStep() {
    pushUndo();
    stepActive_ = true; stepDone_ = 0; stepMoved_ = false; autoTicks_ = 0;
    if (step_.kind == StepMove) moves_ += step_.dir == kN ? 'U' : step_.dir == kS ? 'D' : step_.dir == cc::kW ? 'L' : 'R';
    stepX_ = game_->objX(0); stepY_ = game_->objY(0);
}

// Back to the state before the last step action: the whole game state is restored (map, objects, inventory,
// clock, random generator), so drownings, pick-ups, clones and the rest all come undone.
void App::undoStep() {
    stepActive_ = stepQueued_ = false;
    if (undo_.empty()) return;
    Snapshot& sn = undo_.back();
    globals_ = sn.globals;
    game_ = std::make_unique<Game>(*sn.game);   // refers to globals_, like the original
    game_->setHelmet(helmet_);
    anim_ = sn.anim; attempts_ = sn.attempts; prevX_ = sn.px; prevY_ = sn.py; autoTicks_ = 0;
    moves_.resize(std::min(moves_.size(), sn.moves));
    undo_.pop_back();
    screen_ = Screen::Play;
    synth_.stopAllSfx(); loopHandle_ = 0; loopId_ = 0;
}

void App::update() {
    ++anim_;
    // keep the interpolation base in step even when the game is not ticking (level done, died, paused),
    // otherwise the camera wobbles between the last two positions every frame
    if (game_) for (int i = 0; i < game_->slots() && i < static_cast<int>(prevX_.size()); ++i) { prevX_[i] = game_->objX(i); prevY_[i] = game_->objY(i); }
    if (screen_ != Screen::Play || !game_ || paused_ || skipOffer_ || modal_ != Modal::None) return;
    Input in;
    if (replaying_) {
        auto it = replayInput_.find(replayTick_);
        in.dirs = it == replayInput_.end() ? 0 : it->second;
        in.ab = replayTick_ == 0;     // Tile World starts the level at tick 0 even if the first move comes later
        ++replayTick_;
    } else if (stepMode_) {
        if (!stepActive_ && chipDying()) {
            ++autoTicks_;   // Chip's death animation plays out on its own (Backspace afterwards undoes the fatal step)
        } else {
            if (!stepActive_) {
                if (!stepQueued_) { abPressed_ = false; --anim_; return; }   // step mode: the game (and the tile animation) waits for the next key
                step_ = queued_; stepQueued_ = false; beginStep();
            }
            // a move holds its direction until Chip has started moving (as holding the key would), then lets go
            in.dirs = step_.kind == StepMove && !stepMoved_ ? step_.dir : 0;
            in.ab = step_.kind != StepMove && game_->waiting();   // Space / B start the level without moving
        }
    } else {
        in.dirs = held_;
        in.ab = abPressed_;
    }
    abPressed_ = false;
    bool wasWaiting = game_->waiting();
    game_->tick(in); ++gameTicks_;
    if (sfxOn_) {
        char nm[16];
        for (uint8_t id : game_->sounds()) {
            std::snprintf(nm, sizeof nm, "sfx_%02X", id); synth_.playSfx(song(nm));
            if (std::getenv("PONDER_AUDIO_LOG")) std::fprintf(stderr, "sfx %02X\n", id);
        }
    }
    if (stepActive_) {
        ++stepDone_;
        if (game_->objX(0) != stepX_ || game_->objY(0) != stepY_) stepMoved_ = true;
        // a move (or B) lasts one full move: 4 ticks, then on until Chip stands on a cell (sliding can leave him
        // between cells); Space is a single tick
        bool onCell = (game_->objX(0) & 7) == 0 && (game_->objY(0) & 7) == 0;
        int need = step_.kind == StepTick ? 1 : 4;
        if ((stepDone_ >= need && (onCell || step_.kind == StepTick)) || stepDone_ >= need + 12 || game_->dead() || game_->finished()) {
            stepActive_ = false;
            if (step_.kind != StepMove) moves_.append(static_cast<size_t>(stepDone_), '-');
            // a key still held at the end of a step starts the next one, so holding plays at normal speed and
            // letting go stops at the end of the move
            if (!stepQueued_) {
                uint8_t d = held_ & step_.dir ? step_.dir : held_ & kN ? kN : held_ & kE ? kE : held_ & kS ? kS : held_ & cc::kW ? cc::kW : 0;
                if (d) queueStep(StepMove, d);
                else if (heldB_) queueStep(StepWait, 0);
                else if (heldSpace_) queueStep(StepTick, 0);
            }
        }
    }
    if (wasWaiting && !game_->waiting()) { if (attempts_ < 127) ++attempts_; }
    if (game_->running() && skipTimer_ > 0 && --skipTimer_ == 0 && skipCounter_ > 0) --skipCounter_;
    if (game_->finished()) finishLevel();
    else if (game_->dead()) screen_ = Screen::Died;
}

// ---------------------------------------------------------------- rendering
void App::drawPlayfield(double alpha) {
    const int chipX = game_->objX(0) * 6, chipY = game_->objY(0) * 6;   // 1/8 tile -> px (48/8)
    int px = prevX_[0] * 6, py = prevY_[0] * 6;
    double cxp = px + (chipX - px) * alpha, cyp = py + (chipY - py) * alpha;
    if (std::abs(chipX - px) > kTile || std::abs(chipY - py) > kTile) { cxp = chipX; cyp = chipY; }
    int camX = int(cxp) - 4 * kTile, camY = int(cyp) - 4 * kTile;
    const int maxCam = kMapW * kTile - kViewPx;
    camX = std::clamp(camX, 0, maxCam); camY = std::clamp(camY, 0, maxCam);

    SDL_Rect clip{0, 0, kViewPx, kViewPx};
    SDL_RenderSetClipRect(ren_, &clip);
    int c0 = camX / kTile, r0 = camY / kTile;
    std::vector<int> objs;
    for (int r = r0; r <= r0 + kView && r < kMapH; ++r)
        for (int c = c0; c <= c0 + kView && c < kMapW; ++c) {
            Cell v = game_->cell(r * kMapW + c);
            uint8_t t = static_cast<uint8_t>(v);
            if (isObj(v)) { objs.push_back(objOf(v)); t = game_->objUnder(objOf(v)); }
            if (t >= tile::Count) t = 0;
            if (t != tile::Floor && t != tile::HiddenWall && t != tile::InvisibleWall) {
                // tiles with transparent parts sit on floor
                if (t == tile::Chip || t == tile::ChipUncounted || (t >= tile::Skates && t <= tile::Flippers) ||
                    (t >= tile::KeyRed && t <= tile::KeyGreen) || t == tile::Bomb || t == tile::Hint)
                    assets_.draw(ren_, "tile_00", c * kTile - camX, r * kTile - camY, kTile);
            }
            assets_.draw(ren_, tileSprite(t), c * kTile - camX, r * kTile - camY, kTile);
        }
    for (int i : objs) {
        int x = game_->objX(i) * 6, y = game_->objY(i) * 6;
        int ox = prevX_[i] * 6, oy = prevY_[i] * 6;
        if (std::abs(x - ox) <= kTile && std::abs(y - oy) <= kTile) {
            x = int(ox + (x - ox) * alpha); y = int(oy + (y - oy) * alpha);
        }
        assets_.draw(ren_, objectSprite(i), x - camX, y - camY, kTile);
    }
    SDL_RenderSetClipRect(ren_, nullptr);
}

void App::drawHud() {
    SDL_Rect p{kViewPx, 0, kPanelW, kScreenH};
    ui::panel(ren_, p, SDL_Color{34, 38, 62, 255}, SDL_Color{70, 82, 130, 255});
    int cx = kViewPx + kPanelW / 2;
    char buf[32];
    ui::text(ren_, assets_, false, "LEVEL", cx, 14, kGrey, ui::Center);
    std::snprintf(buf, sizeof buf, "%03d", level_);
    ui::text(ren_, assets_, true, buf, cx, 32, kYellow, ui::Center);
    ui::text(ren_, assets_, false, "TIME", cx, 78, kGrey, ui::Center);
    if (game_->timeLimit() == 0 || game_->timeLeft() == 0) std::snprintf(buf, sizeof buf, "---");
    else std::snprintf(buf, sizeof buf, "%03d", game_->timeLeft());
    ui::text(ren_, assets_, true, buf, cx, 96, game_->timeLeft() && game_->timeLeft() <= 15 ? kRed : kYellow, ui::Center);
    ui::text(ren_, assets_, false, "CHIPS LEFT", cx, 142, kGrey, ui::Center);
    std::snprintf(buf, sizeof buf, "%03d", game_->chipsLeft());
    bool flash = game_->chipsLeft() == 0 && (anim_ & 4);
    ui::text(ren_, assets_, true, buf, cx, 160, flash ? kGreen : kYellow, ui::Center);
    std::snprintf(buf, sizeof buf, "SCORE %07ld", totalScore_);
    ui::text(ren_, assets_, false, buf, cx, 206, kGrey, ui::Center);

    SDL_Rect inv{kViewPx + 14, 250, kPanelW - 28, 108};
    ui::panel(ren_, inv, SDL_Color{22, 24, 40, 255}, SDL_Color{70, 82, 130, 255});
    const char* keys[4] = {"tile_1E", "tile_1F", "tile_20", "tile_21"};
    const char* boots[4] = {"tile_0F", "tile_11", "tile_10", "tile_12"};
    bool have[4] = {game_->skates(), game_->suction(), game_->fireBoots(), game_->flippers()};
    for (int k = 0; k < 4; ++k) {
        int x = inv.x + 6 + k * 44;
        if (game_->key(k)) {
            assets_.draw(ren_, keys[k], x, inv.y + 6, 44);
            if (game_->key(k) > 1) { std::snprintf(buf, sizeof buf, "%d", game_->key(k)); ui::text(ren_, assets_, false, buf, x + 40, inv.y + 30, kWhite, ui::Right); }
        }
        if (have[k]) assets_.draw(ren_, boots[k], x, inv.y + 56, 44);
    }
    const SDL_Color dim{120, 128, 160, 255}, hack{255, 170, 90, 255};
    if (stepMode_ || helmet_ || invEdited_) {
        std::string h;
        for (auto [on, name] : {std::pair{stepMode_, "STEP"}, std::pair{helmet_, "HELMET"}, std::pair{invEdited_, "INV"}})
            if (on) h += (h.empty() ? "HACK: " : "+") + std::string(name);
        ui::text(ren_, assets_, false, h.c_str(), cx, 362, hack, ui::Center, false);
    }
    if (stepMode_) {
        ui::text(ren_, assets_, false, "Space tick  B wait", cx, 384, dim, ui::Center, false);
        ui::text(ren_, assets_, false, "Bksp undo  R restart", cx, 406, dim, ui::Center, false);
    } else {
        ui::text(ren_, assets_, false, "P pause  R restart", cx, 384, dim, ui::Center, false);
        ui::text(ren_, assets_, false, "ESC menu", cx, 406, dim, ui::Center, false);
    }
}

// Strict mode: an edge case has reached cartridge memory or behaviour the remake does not reproduce exactly
// (doc 04 §4.4). Say so for the rest of the attempt instead of silently drifting from the real game; the "?"
// button opens a short explanation of the general case and of this glitch.
// Odd tiles 67 / 6C drawn on screen overwrite sound data on the cartridge (doc 08 §3) without affecting play:
// a quiet one-line note at the foot of the play area, for the rest of the attempt.
void App::drawSoundNote() {
    if (!game_ || !game_->soundGlitch() || (screen_ != Screen::Play && screen_ != Screen::Died)) return;
    const char* msg = game_->soundGlitch() == 0x67 ? "Lynx CC1 would play a different ice sound here." : "Lynx CC1 would play different music here.";
    SDL_Rect b{24, kViewPx - 38, kViewPx - 48, 28};
    ui::panel(ren_, b, SDL_Color{20, 26, 44, 190}, SDL_Color{90, 110, 160, 255});
    ui::text(ren_, assets_, false, msg, kViewPx / 2, b.y + 5, SDL_Color{170, 190, 230, 255}, ui::Center, false);
}

void App::drawDesync() {
    if (!game_ || !game_->outOfSync() || (screen_ != Screen::Play && screen_ != Screen::Died)) return;
    const int mid = kViewPx / 2;
    const int why = game_->desyncReason();
    SDL_Rect b{24, 12, kViewPx - 48, 84};
    ui::panel(ren_, b, SDL_Color{40, 18, 22, 225}, SDL_Color{255, 140, 64, 255});
    ui::text(ren_, assets_, true, "Desync with Lynx CC1", mid, b.y + 8, SDL_Color{255, 170, 90, 255}, ui::Center);
    ui::text(ren_, assets_, false, why == 3 ? "A rare glitch is likely to crash Lynx CC1." : why == 2 ? "A rare glitch hit behaviour not yet mapped." : "A rare glitch reached unmapped memory.", mid, b.y + 40, kWhite, ui::Center, false);
    ui::text(ren_, assets_, false, why == 3 ? "The remake plays on; the cartridge may not." : "Lynx CC1 may differ on play from now on.", mid, b.y + 60, kWhite, ui::Center, false);
    SDL_Rect q = desyncButton();
    ui::panel(ren_, q, desyncInfo_ ? SDL_Color{255, 140, 64, 255} : SDL_Color{70, 30, 30, 255}, SDL_Color{255, 170, 90, 255});
    ui::text(ren_, assets_, false, "?", q.x + q.w / 2, q.y + 3, kWhite, ui::Center);
    if (!desyncInfo_) return;
    static const std::vector<std::string> kGeneral[4] = {{}, {"The original keeps working data in parts of", "the Lynx's memory that this remake does not", "copy, and a rare glitch has made the game", "depend on it. The remake carries on with its", "best guess, so the real cartridge may play out", "differently from here."}, {"This glitch is understood, but its exact rule", "on the Lynx has not been measured yet. The", "remake follows the closest rule it knows, so", "the real cartridge may play out differently", "from here."}, {"On the Lynx this glitch damages the game's", "own program. Usually the cartridge crashes", "soon after, often when the screen next", "scrolls, but when and whether depends on", "program code the remake does not copy. The", "remake carries on with normal rules."}};
    static const std::vector<std::string> kDetail[9] = {{}, {"Here a move made while the cell lookup was", "broken (code 38 drawn at x = 96) read scratch", "memory the remake does not hold."}, {"Here code 6E has damaged the tile-animation", "program; until the game crashes a few ticks", "later, animated tiles (water, fire, teleport,", "exit) can write their positions into untracked", "memory."}, {"Here an object entered a teleport while the", "cell lookup was broken (code 38 at x = 96),", "and the Lynx's teleport search wanders through", "untracked memory."}, {"Here an object is boxed in on an odd tile that", "moves it on at once, and bounces without end;", "on the Lynx this overruns the stack, so what", "follows depends on leftover stack contents."}, {"Here a button's link was overwritten by", "drawing an odd tile, so it points into sprite", "or program memory, and the Lynx reads whatever", "is stored there."}, {"Here a stray object (state F5) has overwritten", "the game's row lookup table while the screen", "scrolls; on the Lynx this can stop objects", "being drawn, and the rule for a scrolling", "screen is not mapped."}, {"Here an object in state 7B was drawn on", "screen; drawing it writes its position into", "program code. Odd tile 47 can cause this: it", "writes Chip's screen position into object", "state bytes, and a position of 7B becomes", "that state."}, {"Here odd tile 71 was reached in a way whose", "outcome on the Lynx depends on the sound", "driver's working memory, which follows the", "music (Chip stepping onto it, or an object", "standing on it or blocked on it)."}};
    const auto& G = kGeneral[(why >= 1 && why <= 3) ? why : 1];
    int d = game_->desyncDetail();
    const auto& D = kDetail[(d >= 1 && d <= 8) ? d : 0];
    int n = static_cast<int>(G.size() + D.size()) + (D.empty() ? 0 : 1);
    SDL_Rect t{b.x, b.y + b.h + 6, b.w, 16 + 20 * n};
    ui::panel(ren_, t, SDL_Color{24, 14, 18, 240}, SDL_Color{255, 140, 64, 255});
    int y = t.y + 8;
    for (const auto& l : G) { ui::text(ren_, assets_, false, l, t.x + 12, y, kWhite, ui::Left, false); y += 20; }
    if (!D.empty()) y += 20;
    for (const auto& l : D) { ui::text(ren_, assets_, false, l, t.x + 12, y, SDL_Color{255, 200, 140, 255}, ui::Left, false); y += 20; }
}

void App::drawOverlay() {
    auto box = [&](int h) {
        SDL_Rect b{24, kViewPx / 2 - h / 2, kViewPx - 48, h};
        ui::panel(ren_, b, SDL_Color{16, 18, 34, 220}, SDL_Color{255, 214, 64, 255});
        return b;
    };
    int mid = kViewPx / 2;
    char buf[64];
    if (skipOffer_) {
        SDL_Rect b = box(170);
        ui::text(ren_, assets_, true, "Need a hand?", mid, b.y + 14, kYellow, ui::Center);
        ui::text(ren_, assets_, false, "This level has been tough.", mid, b.y + 56, kWhite, ui::Center);
        ui::text(ren_, assets_, false, "Skip ahead to the next one?", mid, b.y + 78, kWhite, ui::Center);
        ui::text(ren_, assets_, true, skipYes_ ? "> YES <     NO" : "  YES     > NO <", mid, b.y + 112, kCyan, ui::Center);
        return;
    }
    if (screen_ == Screen::Play && (game_->waiting() || paused_)) {
        SDL_Rect b = box(150);
        ui::text(ren_, assets_, true, paused_ ? "PAUSED" : data_.title, mid, b.y + 16, kYellow, ui::Center);
        if (paused_) ui::text(ren_, assets_, false, data_.title, mid, b.y + 60, kWhite, ui::Center);
        std::snprintf(buf, sizeof buf, "Password: %s", passwords_[level_ - 1].c_str());
        ui::text(ren_, assets_, false, buf, mid, b.y + 84, kCyan, ui::Center);
        if (!paused_) ui::text(ren_, assets_, false, "Move to start", mid, b.y + 112, kGrey, ui::Center);
        return;
    }
    if (screen_ == Screen::Play && game_->chipOnHint() && !data_.hint.empty()) {
        int h = 30 + 22 * int(data_.hint.size());
        SDL_Rect b{24, kViewPx - h - 16, kViewPx - 48, h};
        ui::panel(ren_, b, SDL_Color{16, 18, 34, 225}, SDL_Color{120, 230, 255, 255});
        for (size_t k = 0; k < data_.hint.size(); ++k)
            ui::text(ren_, assets_, false, data_.hint[k], mid, b.y + 14 + 22 * int(k), kWhite, ui::Center);
        return;
    }
    if (screen_ == Screen::Died) {
        SDL_Rect b = box(130);
        bool timeout = game_->deathReason() == DeathReason::TimeOut;
        bool crash = game_->deathReason() == DeathReason::Crash;
        ui::text(ren_, assets_, true, timeout ? "Time's up!" : crash ? "Cartridge crash!" : "Ouch!", mid, b.y + 18, kRed, ui::Center);
        if (crash) ui::text(ren_, assets_, false, "The original game would crash here", mid, b.y + 52, kWhite, ui::Center);
        ui::text(ren_, assets_, false, stepMode_ && !undo_.empty() ? "Enter: try again   Bksp: undo" : "Press Enter to try again", mid, b.y + 78, kWhite, ui::Center);
        return;
    }
    if (screen_ == Screen::LevelDone) {
        static const char* praise[5] = {"Perfect - first try!", "Nicely done!", "Great work!", "Well earned!", "Persistence pays off!"};
        int a = attempts_ - 1, idx = a < 1 ? 0 : a < 3 ? 1 : a < 5 ? 2 : a < 10 ? 3 : 4;
        SDL_Rect b = box(210);
        ui::text(ren_, assets_, true, praise[idx], mid, b.y + 14, kGreen, ui::Center);
        std::snprintf(buf, sizeof buf, "Time bonus   %5ld", timeBonus_); ui::text(ren_, assets_, false, buf, mid, b.y + 62, kWhite, ui::Center);
        std::snprintf(buf, sizeof buf, "Level bonus  %5ld", levelBonus_); ui::text(ren_, assets_, false, buf, mid, b.y + 86, kWhite, ui::Center);
        std::snprintf(buf, sizeof buf, "Level score  %5ld", timeBonus_ + levelBonus_); ui::text(ren_, assets_, false, buf, mid, b.y + 110, kWhite, ui::Center);
        std::snprintf(buf, sizeof buf, "Total score  %07ld", totalScore_); ui::text(ren_, assets_, false, buf, mid, b.y + 140, kYellow, ui::Center);
        ui::text(ren_, assets_, false, "Press Enter for the next level", mid, b.y + 176, kGrey, ui::Center);
    }
}

void App::drawTitle(double alpha) {
    // a field of tiles scrolling smoothly left behind the title; the pattern index follows the world column,
    // so wrapping the pixel offset never makes the pattern jump
    const int scroll = int((anim_ + alpha) * 2.0);
    const int base = scroll / kTile, off = scroll % kTile;
    static const char* deco[] = {"tile_00", "tile_23", "tile_00", "tile_02", "tile_00", "tile_28"};
    for (int r = 0; r < kScreenH / kTile + 1; ++r)
        for (int c = 0; c < kScreenW / kTile + 2; ++c)
            assets_.draw(ren_, deco[(r * 7 + (c + base) * 3) % 6], c * kTile - off, r * kTile, kTile, 150);
    ui::panel(ren_, SDL_Rect{60, 50, kScreenW - 120, 332}, SDL_Color{16, 18, 34, 230}, SDL_Color{255, 214, 64, 255});
    ui::text(ren_, assets_, true, "PONDER PUZZLERS", kScreenW / 2, 70, kYellow, ui::Center);
    ui::text(ren_, assets_, false, set_.name, kScreenW / 2, 112, kWhite, ui::Center);
    assets_.draw(ren_, "hero_2_1", kScreenW / 2 - 84, 140, 56);
    assets_.draw(ren_, "obj_2_1_0", kScreenW / 2 - 28, 140, 56);
    assets_.draw(ren_, "tile_23", kScreenW / 2 + 28, 140, 56);
    // rules mode: two checkboxes, exactly one ticked
    const char* labels[2] = {"Strict LYNX ROM", "Extended LYNX mode"};
    for (int k = 0; k < 2; ++k) {
        bool on = (k == 1) == extended_;
        SDL_Rect box = modeBox(k);
        ui::panel(ren_, box, SDL_Color{34, 38, 62, 255}, on ? kYellow : SDL_Color{110, 120, 160, 255});
        if (on) {
            SDL_SetRenderDrawColor(ren_, 255, 214, 64, 255);
            for (int w = -1; w <= 1; ++w) {
                SDL_RenderDrawLine(ren_, box.x + 4, box.y + 9 + w, box.x + 8, box.y + 14 + w);
                SDL_RenderDrawLine(ren_, box.x + 8, box.y + 14 + w, box.x + 15, box.y + 4 + w);
            }
        }
        ui::text(ren_, assets_, false, labels[k], box.x + 30, box.y - 1, on ? kWhite : kGrey, ui::Left);
    }
    std::string note = extended_ ? "Tile World style: level wiring, all thin walls, no object limit"
                     : strictAltered_ ? "Only what the cartridge can do - " + std::to_string(strictAltered_) + " level(s) adapted to fit"
                                      : "Exactly what the original cartridge can do";
    ui::text(ren_, assets_, false, note, kScreenW / 2, 270, SDL_Color{150, 158, 190, 255}, ui::Center, false);
    if ((anim_ / 10) & 1) ui::text(ren_, assets_, true, "Press Enter", kScreenW / 2, 296, kCyan, ui::Center);
    ui::text(ren_, assets_, false, "Up/Down or M: rules   Arrows move   P pause   R restart", kScreenW / 2, 346, kGrey, ui::Center, false);
}

void App::drawPassword(double alpha) {
    drawTitle(alpha);
    ui::panel(ren_, SDL_Rect{100, 120, kScreenW - 200, 200}, SDL_Color{16, 18, 34, 245}, SDL_Color{120, 230, 255, 255});
    ui::text(ren_, assets_, false, "Enter a level password,", kScreenW / 2, 140, kWhite, ui::Center);
    ui::text(ren_, assets_, false, "or press Enter to start here.", kScreenW / 2, 162, kWhite, ui::Center);
    for (int k = 0; k < 4; ++k) {
        int x = kScreenW / 2 - 90 + k * 48;
        ui::panel(ren_, SDL_Rect{x, 200, 40, 52}, SDL_Color{34, 38, 62, 255}, k == pwCursor_ ? kYellow : SDL_Color{70, 82, 130, 255});
        ui::text(ren_, assets_, true, std::string(1, pw_[k]), x + 20, 208, k == pwCursor_ ? kYellow : kWhite, ui::Center);
    }
    ui::text(ren_, assets_, false, "Type letters or use the arrows", kScreenW / 2, 276, kGrey, ui::Center);
}

void App::render(double alpha) {
    SDL_SetRenderDrawColor(ren_, 12, 12, 24, 255);
    SDL_RenderSetViewport(ren_, nullptr);
    SDL_RenderClear(ren_);
    SDL_Rect game{0, kMenuH, kScreenW, kScreenH};
    SDL_RenderSetViewport(ren_, &game);              // the game draws in its own coordinates below the menu bar
    switch (screen_) {
    case Screen::Title: drawTitle(alpha); break;
    case Screen::Password: drawPassword(alpha); break;
    case Screen::Ending:
        drawTitle(alpha);
        ui::panel(ren_, SDL_Rect{60, 120, kScreenW - 120, 190}, SDL_Color{16, 18, 34, 245}, kGreen);
        ui::text(ren_, assets_, true, "Congratulations,", kScreenW / 2, 140, kGreen, ui::Center);
        ui::text(ren_, assets_, false, "you have completed the levelset!", kScreenW / 2, 176, kGreen, ui::Center);
        { char b[48]; std::snprintf(b, sizeof b, "Total score %07ld", totalScore_); ui::text(ren_, assets_, false, b, kScreenW / 2, 200, kWhite, ui::Center); }
        ui::text(ren_, assets_, false, "Press Enter", kScreenW / 2, 250, kCyan, ui::Center);
        break;
    default:
        drawPlayfield(alpha); drawHud(); drawOverlay(); drawSoundNote(); drawDesync();
        break;
    }
    SDL_RenderSetViewport(ren_, nullptr);
    drawMenuBar();
    drawModal();
    SDL_RenderPresent(ren_);
}

// ---------------------------------------------------------------- audio
static void audioCallback(void* user, Uint8* stream, int len) {
    static_cast<audio::Synth*>(user)->render(reinterpret_cast<float*>(stream), len / static_cast<int>(2 * sizeof(float)));
}

void App::initAudio() {
    namespace fs = std::filesystem;
    std::error_code ec;
    for (fs::directory_iterator it(fs::path(opt_.assets) / "audio", ec), end; !ec && it != end; it.increment(ec)) {
        if (it->path().extension() != ".song") continue;
        try { songs_[it->path().stem().string()] = audio::loadSong(it->path().string()); }
        catch (const std::exception& e) { std::fprintf(stderr, "audio: %s\n", e.what()); }
    }
    if (SDL_InitSubSystem(SDL_INIT_AUDIO) != 0) { std::fprintf(stderr, "audio: %s\n", SDL_GetError()); return; }
    SDL_AudioSpec want{}, have{};
    want.freq = synth_.rate(); want.format = AUDIO_F32SYS; want.channels = 2; want.samples = 1024;
    want.callback = audioCallback; want.userdata = &synth_;
    audioDev_ = SDL_OpenAudioDevice(nullptr, 0, &want, &have, 0);
    if (!audioDev_) { std::fprintf(stderr, "audio: %s\n", SDL_GetError()); return; }
    SDL_PauseAudioDevice(audioDev_, 0);
}

// Level music: the cartridge picks track 1-13 from the 3rd letter of the level's password (doc 01 §7);
// passwords without letters there fall back to the level number.
std::string App::levelTrack() const {
    int k = (level_ - 1) % 13;
    if (level_ >= 1 && level_ <= maxLevel()) {
        const std::string& pw = passwords_[level_ - 1];
        if (pw.size() >= 3 && pw[2] >= 'A' && pw[2] <= 'Z') k = (pw[2] - 'A') >> 1;
        else if (pw.size() >= 3 && pw[2] >= 'a' && pw[2] <= 'z') k = (pw[2] - 'a') >> 1;
    }
    char nm[16]; std::snprintf(nm, sizeof nm, "music_%02d", k + 1);
    return nm;
}

void App::updateAudio() {
    if (!audioDev_) return;
    const audio::Song* want = nullptr;
    switch (screen_) {
        case Screen::Title: case Screen::Password: want = song("music_title"); break;
        case Screen::Ending: want = song("music_ending"); break;
        default: want = song(levelTrack()); break;
    }
    if (!musicOn_) want = nullptr;
    if (want != curMusic_ || restartMusic_) {
        synth_.playMusic(want); curMusic_ = want;
        if (std::getenv("PONDER_AUDIO_LOG")) std::fprintf(stderr, "music %s\n", want ? want->name.c_str() : "(off)");
    }
    restartMusic_ = false;
    synth_.setPaused(paused_ && screen_ == Screen::Play);
    // looping ice / force-floor sound, owned by the game state (doc 08 §3)
    uint8_t loop = 0;
    if (sfxOn_ && screen_ == Screen::Play && game_ && !paused_ && modal_ == Modal::None) loop = game_->loopSound();
    if (loop != loopId_) {
        if (loopHandle_) synth_.stopSfx(loopHandle_);
        loopHandle_ = 0;
        if (loop) { char nm[16]; std::snprintf(nm, sizeof nm, "sfx_%02X", loop); loopHandle_ = synth_.playSfx(song(nm), true); }
        if (std::getenv("PONDER_AUDIO_LOG")) std::fprintf(stderr, "loop %02X\n", loop);
        loopId_ = loop;
    }
}

// ---------------------------------------------------------------- menus and dialogs
const SDL_Color kBarFill{28, 31, 52, 255}, kBarLine{70, 82, 130, 255}, kHover{60, 70, 120, 255}, kDialogFill{20, 22, 40, 250};

SDL_Rect App::menuTitleRect(int m) const {
    int x = 6;
    for (int k = 0; k < m; ++k) x += ui::textWidth(assets_, false, menus_[k].title) + 24;
    return SDL_Rect{x, 0, ui::textWidth(assets_, false, menus_[m].title) + 20, kMenuH};
}

SDL_Rect App::dropRect(int m) const {
    int w = 0;
    for (auto& it : menus_[m].items)
        if (it.label) w = std::max(w, ui::textWidth(assets_, false, it.label) + ui::textWidth(assets_, false, it.keys) + 56);
    int h = 8;
    for (auto& it : menus_[m].items) h += it.label ? 26 : 9;
    SDL_Rect t = menuTitleRect(m);
    return SDL_Rect{t.x, kMenuH, w, h};
}

SDL_Rect App::menuItemRect(int m, int k) const {
    SDL_Rect d = dropRect(m);
    int y = d.y + 4;
    for (int j = 0; j < k; ++j) y += menus_[m].items[j].label ? 26 : 9;
    return SDL_Rect{d.x + 4, y, d.w - 8, menus_[m].items[k].label ? 26 : 9};
}

void App::drawMenuBar() {
    SDL_Rect bar{0, 0, kScreenW, kMenuH};
    SDL_SetRenderDrawColor(ren_, kBarFill.r, kBarFill.g, kBarFill.b, 255);
    SDL_RenderFillRect(ren_, &bar);
    SDL_SetRenderDrawColor(ren_, kBarLine.r, kBarLine.g, kBarLine.b, 255);
    SDL_RenderDrawLine(ren_, 0, kMenuH - 1, kScreenW, kMenuH - 1);
    for (int m = 0; m < static_cast<int>(menus_.size()); ++m) {
        SDL_Rect r = menuTitleRect(m);
        if (modal_ == Modal::Menu && menuOpen_ == m) {
            SDL_SetRenderDrawColor(ren_, kHover.r, kHover.g, kHover.b, 255);
            SDL_RenderFillRect(ren_, &r);
        }
        ui::text(ren_, assets_, false, menus_[m].title, r.x + 10, 3, kWhite, ui::Left, false);
    }
    // what is loaded, right-aligned
    std::string src = !opt_.levels.empty() ? set_.name : !opt_.rom.empty() ? "Cartridge" : "Built-in levels";
    ui::text(ren_, assets_, false, src + (extended_ ? "  |  Extended" : "  |  Strict"), kScreenW - 10, 3,
             SDL_Color{140, 148, 180, 255}, ui::Right, false);
}

std::string App::levelRanges() const {
    std::string out;
    int start = -1, prev = -1;
    auto flush = [&]() {
        if (start < 0) return;
        if (!out.empty()) out += ", ";
        out += std::to_string(start);
        if (prev != start) out += " - " + std::to_string(prev);
    };
    for (const auto& L : set_.levels) {
        if (L.endMarker) continue;
        if (start >= 0 && L.number == prev + 1) { prev = L.number; continue; }
        flush(); start = prev = L.number;
    }
    flush();
    return out;
}

void App::drawModal() {
    const int mid = kScreenW / 2;
    auto dim = [&]() {
        SDL_SetRenderDrawBlendMode(ren_, SDL_BLENDMODE_BLEND);
        SDL_SetRenderDrawColor(ren_, 0, 0, 0, 130);
        SDL_Rect all{0, kMenuH, kScreenW, kScreenH};
        SDL_RenderFillRect(ren_, &all);
    };
    auto button = [&](SDL_Rect r, const char* label, bool primary) {
        ui::panel(ren_, r, primary ? SDL_Color{50, 64, 120, 255} : SDL_Color{34, 38, 62, 255}, primary ? kCyan : kBarLine);
        ui::text(ren_, assets_, false, label, r.x + r.w / 2, r.y + 5, kWhite, ui::Center, false);
    };
    switch (modal_) {
    case Modal::None: return;
    case Modal::Menu: {
        SDL_Rect d = dropRect(menuOpen_);
        ui::panel(ren_, d, kBarFill, kBarLine);
        for (int k = 0; k < static_cast<int>(menus_[menuOpen_].items.size()); ++k) {
            const MenuItem& it = menus_[menuOpen_].items[k];
            SDL_Rect r = menuItemRect(menuOpen_, k);
            if (!it.label) {
                SDL_SetRenderDrawColor(ren_, kBarLine.r, kBarLine.g, kBarLine.b, 255);
                SDL_RenderDrawLine(ren_, r.x + 6, r.y + 4, r.x + r.w - 6, r.y + 4);
                continue;
            }
            if (k == menuHover_) { SDL_SetRenderDrawColor(ren_, kHover.r, kHover.g, kHover.b, 255); SDL_RenderFillRect(ren_, &r); }
            int lx = r.x + 10;
            if (isToggle(it.cmd)) {
                bool on = toggleOn(it.cmd);
                SDL_Rect box{r.x + 8, r.y + 5, 15, 15};
                ui::panel(ren_, box, SDL_Color{34, 38, 62, 255}, on ? kYellow : kBarLine);
                if (on) {
                    SDL_SetRenderDrawColor(ren_, 255, 214, 64, 255);
                    SDL_RenderDrawLine(ren_, box.x + 3, box.y + 7, box.x + 6, box.y + 11);
                    SDL_RenderDrawLine(ren_, box.x + 6, box.y + 11, box.x + 12, box.y + 3);
                }
                lx = r.x + 30;
            }
            ui::text(ren_, assets_, false, it.label, lx, r.y + 3, kWhite, ui::Left, false);
            ui::text(ren_, assets_, false, it.keys, r.x + r.w - 10, r.y + 3, kGrey, ui::Right, false);
        }
        return;
    }
    case Modal::LevelDialog: {
        dim();
        SDL_Rect b{mid - 170, kMenuH + 110, 340, 196};
        ui::panel(ren_, b, kDialogFill, kYellow);
        ui::text(ren_, assets_, true, "Level", mid, b.y + 12, kYellow, ui::Center);
        SDL_Rect field{mid - 70, b.y + 56, 140, 40};
        ui::panel(ren_, field, SDL_Color{34, 38, 62, 255}, kCyan);
        std::string shown = levelInput_ + (((SDL_GetTicks() / 500) & 1) ? "_" : " ");
        ui::text(ren_, assets_, true, shown, mid, field.y + 2, kWhite, ui::Center, false);
        ui::text(ren_, assets_, false, "Range: " + levelRanges(), mid, b.y + 104, kGrey, ui::Center, false);
        if (!dialogError_.empty()) ui::text(ren_, assets_, false, dialogError_, mid, b.y + 126, kRed, ui::Center, false);
        button(SDL_Rect{mid - 120, b.y + 150, 110, 30}, "OK", true);
        button(SDL_Rect{mid + 10, b.y + 150, 110, 30}, "Cancel", false);
        return;
    }
    case Modal::Moves: {
        dim();
        SDL_Rect b{mid - 280, kMenuH + 40, 560, 350};
        ui::panel(ren_, b, kDialogFill, kYellow);
        char head[64]; std::snprintf(head, sizeof head, "Moves (%zu)", moves_.size());
        ui::text(ren_, assets_, true, head, mid, b.y + 8, kYellow, ui::Center);
        if (moves_.empty()) {
            ui::text(ren_, assets_, false, stepMode_ ? "No steps yet this attempt." : "Moves are recorded in Step Mode (Hacks menu).", mid, b.y + 120, kGrey, ui::Center, false);
        } else {
            // groups of 10 for easier counting, wrapped to the box; the newest lines are shown if it is long
            std::vector<std::string> lines; std::string cur;
            for (size_t i = 0; i < moves_.size(); i += 10) {
                std::string grp = moves_.substr(i, 10);
                if (!cur.empty() && ui::textWidth(assets_, false, cur + " " + grp) > b.w - 40) { lines.push_back(cur); cur.clear(); }
                cur += (cur.empty() ? "" : " ") + grp;
            }
            if (!cur.empty()) lines.push_back(cur);
            const size_t maxLines = 9;
            size_t first = lines.size() > maxLines ? lines.size() - maxLines : 0;
            if (first) ui::text(ren_, assets_, false, "... (" + std::to_string(first) + " earlier lines; Copy takes all)", mid, b.y + 50, kGrey, ui::Center, false);
            for (size_t k = first; k < lines.size(); ++k)
                ui::text(ren_, assets_, false, lines[k], b.x + 20, b.y + 72 + int(k - first) * 24, kWhite, ui::Left, false);
        }
        ui::text(ren_, assets_, false, "U D L R move   - wait a tick", mid, b.y + b.h - 76, kGrey, ui::Center, false);
        button(SDL_Rect{mid - 120, b.y + b.h - 44, 110, 30}, movesCopied_ ? "Copied" : "Copy", true);
        button(SDL_Rect{mid + 10, b.y + b.h - 44, 110, 30}, "Close", false);
        return;
    }
    case Modal::Inventory: {
        dim();
        SDL_Rect b = invBox();
        ui::panel(ren_, b, kDialogFill, kYellow);
        ui::text(ren_, assets_, true, "Inventory", mid, b.y + 8, kYellow, ui::Center);
        static const char* names[8] = {"Red keys", "Blue keys", "Yellow keys", "Green keys", "Ice skates", "Suction boots", "Fire boots", "Flippers"};
        static const char* icons[8] = {"tile_1E", "tile_1F", "tile_20", "tile_21", "tile_0F", "tile_11", "tile_10", "tile_12"};
        for (int r = 0; r < 8; ++r) {
            SDL_Rect rr = invRowRect(r);
            if (r == invRow_) { SDL_SetRenderDrawColor(ren_, kHover.r, kHover.g, kHover.b, 255); SDL_RenderFillRect(ren_, &rr); }
            assets_.draw(ren_, "tile_00", rr.x + 2, rr.y + 1, 32);
            assets_.draw(ren_, icons[r], rr.x + 2, rr.y + 1, 32);
            ui::text(ren_, assets_, false, names[r], rr.x + 44, rr.y + 5, kWhite, ui::Left, false);
            if (r < 4) {
                char buf[8]; std::snprintf(buf, sizeof buf, "%d", inv_[r]);
                ui::text(ren_, assets_, false, "<", rr.x + rr.w - 130, rr.y + 5, kCyan, ui::Center, false);
                ui::text(ren_, assets_, false, buf, rr.x + rr.w - 75, rr.y + 5, kYellow, ui::Center, false);
                ui::text(ren_, assets_, false, ">", rr.x + rr.w - 20, rr.y + 5, kCyan, ui::Center, false);
            } else {
                SDL_Rect box{rr.x + rr.w - 34, rr.y + 8, 18, 18};
                ui::panel(ren_, box, SDL_Color{34, 38, 62, 255}, inv_[r] ? kYellow : kBarLine);
                if (inv_[r]) {
                    SDL_SetRenderDrawColor(ren_, 255, 214, 64, 255);
                    SDL_RenderDrawLine(ren_, box.x + 4, box.y + 9, box.x + 7, box.y + 13);
                    SDL_RenderDrawLine(ren_, box.x + 7, box.y + 13, box.x + 14, box.y + 4);
                }
            }
        }
        button(SDL_Rect{mid - 120, b.y + b.h - 44, 110, 30}, "OK", true);
        button(SDL_Rect{mid + 10, b.y + b.h - 44, 110, 30}, "Cancel", false);
        return;
    }
    case Modal::Waiting: {
        dim();
        SDL_Rect b{mid - 210, kMenuH + 160, 420, 90};
        ui::panel(ren_, b, kDialogFill, kCyan);
        ui::text(ren_, assets_, false, "Choose a file in the file dialog window", mid, b.y + 20, kWhite, ui::Center, false);
        ui::text(ren_, assets_, false, "Esc cancels", mid, b.y + 50, kGrey, ui::Center, false);
        return;
    }
    case Modal::Message: {
        dim();
        SDL_Rect b{mid - 230, kMenuH + 140, 460, 130};
        ui::panel(ren_, b, kDialogFill, kRed);
        // wrap the message to the box
        std::vector<std::string> lines; std::string cur, word;
        auto push = [&]() {
            if (word.empty()) return;
            if (!cur.empty() && ui::textWidth(assets_, false, cur + " " + word) > b.w - 30) { lines.push_back(cur); cur.clear(); }
            cur += (cur.empty() ? "" : " ") + word; word.clear();
        };
        for (char ch : message_) { if (ch == ' ') push(); else word += ch; }
        push(); if (!cur.empty()) lines.push_back(cur);
        for (size_t k = 0; k < lines.size() && k < 3; ++k) ui::text(ren_, assets_, false, lines[k], mid, b.y + 16 + 22 * int(k), kWhite, ui::Center, false);
        button(SDL_Rect{mid - 55, b.y + 90, 110, 30}, "OK", true);
        return;
    }
    case Modal::Browser: {
        dim();
        SDL_Rect b{30, kMenuH + 14, kScreenW - 60, kScreenH - 28};
        ui::panel(ren_, b, kDialogFill, kCyan);
        ui::text(ren_, assets_, false, browserPurpose_ == CmdLoadRom ? "Load ROM (.lnx)" : "Load Level Pack (.dat, .ccl)", b.x + 14, b.y + 8, kYellow, ui::Left, false);
        std::string dir = browserDir_;
        while (ui::textWidth(assets_, false, dir) > b.w - 28 && dir.size() > 4) dir = "..." + dir.substr(4);
        ui::text(ren_, assets_, false, dir, b.x + 14, b.y + 30, kGrey, ui::Left, false);
        SDL_Rect list{b.x + 10, b.y + 56, b.w - 20, b.h - 104};
        ui::panel(ren_, list, SDL_Color{14, 16, 30, 255}, kBarLine);
        const int rows = (list.h - 8) / 22;
        SDL_RenderSetClipRect(ren_, &list);
        for (int r = 0; r < rows && browserTop_ + r < static_cast<int>(entries_.size()); ++r) {
            int k = browserTop_ + r;
            SDL_Rect row{list.x + 4, list.y + 4 + r * 22, list.w - 8, 22};
            if (k == browserSel_) { SDL_SetRenderDrawColor(ren_, kHover.r, kHover.g, kHover.b, 255); SDL_RenderFillRect(ren_, &row); }
            const Entry& en = entries_[k];
            ui::text(ren_, assets_, false, en.dir ? "[" + en.name + "]" : en.name, row.x + 8, row.y + 1, en.dir ? kCyan : kWhite, ui::Left, false);
        }
        SDL_RenderSetClipRect(ren_, nullptr);
        if (entries_.empty()) ui::text(ren_, assets_, false, "(no matching files here)", mid, list.y + 20, kGrey, ui::Center, false);
        ui::text(ren_, assets_, false, "Enter open   Backspace up   Esc cancel", b.x + 14, b.y + b.h - 38, kGrey, ui::Left, false);
        button(SDL_Rect{b.x + b.w - 250, b.y + b.h - 42, 110, 30}, "Open", true);
        button(SDL_Rect{b.x + b.w - 130, b.y + b.h - 42, 110, 30}, "Cancel", false);
        return;
    }
    }
}

void App::resetProgress() {
    game_.reset(); held_ = 0; paused_ = false; replaying_ = false;
    level_ = 1; totalScore_ = 0; attempts_ = 0; skipCounter_ = 10; skipOffer_ = false;
    screen_ = Screen::Title;
}

void App::loadRomFile(const std::string& path) {
    Options before = opt_;
    try {
        Rom rom(path);                              // validates the image
        opt_.rom = path; opt_.levels.clear();
        loadSet();
        resetProgress();
    } catch (const std::exception& e) {
        opt_ = before;
        showMessage(std::string("Could not load ROM: ") + e.what());
    }
}

void App::loadPackFile(const std::string& path) {
    Options before = opt_;
    try {
        opt_.levels = path;                         // a loaded ROM stays in use for its exact tables
        loadSet();
        if (set_.levels.empty()) throw std::runtime_error("the level pack is empty");
        resetProgress();
    } catch (const std::exception& e) {
        opt_ = before;
        try { loadSet(); } catch (...) {}
        showMessage(std::string("Could not load level pack: ") + e.what());
    }
}

static std::string lowerExt(const std::string& name) {
    auto dot = name.find_last_of('.');
    std::string e = dot == std::string::npos ? "" : name.substr(dot + 1);
    for (auto& c : e) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return e;
}

// Native file dialog through zenity or kdialog when present. It runs as a separate process and the game keeps
// running (and redrawing) while it is open: waiting for it inside the click froze both windows, because the
// game window still held the mouse grab of the unfinished click.
// The dialog is a separate program, so the window manager may put it behind the game. Both tools can be told the
// game window's X11 id (`--attach`): the dialog then belongs to the game window and opens on top of it. Older
// zenity (GTK 3) and kdialog support it; zenity 4 dropped the option, so it is only passed when the tool's help
// lists it. Under Wayland there is no X11 id and nothing is attached.
static std::string attachArg(const char* tool, unsigned long xid) {
    if (!xid) return "";
    std::string probe = std::string(tool) + (std::string(tool) == "zenity" ? " --help-general" : " --help") + " 2>&1 | grep -q -- --attach";
    if (std::system(probe.c_str()) != 0) return "";
    return std::string(tool) == "zenity" ? " --modal --attach=" + std::to_string(xid) : " --attach " + std::to_string(xid);
}

static std::string nativeDialogCommand(bool rom, const std::string& startDir, unsigned long xid) {
    auto has = [](const char* tool) { return std::system((std::string("command -v ") + tool + " >/dev/null 2>&1").c_str()) == 0; };
    std::string dir = startDir.empty() ? "." : startDir;
    auto q = [](const std::string& s) { std::string r = "'"; for (char c : s) { if (c == '\'') r += "'\\''"; else r += c; } return r + "'"; };
    if (has("zenity"))
        return "zenity --file-selection" + attachArg("zenity", xid) + " --title=" + q(rom ? "Load ROM" : "Load Level Pack") + " --filename=" + q(dir + "/") +
               (rom ? " --file-filter='Lynx ROM (*.lnx) | *.lnx *.LNX' --file-filter='All files | *'"
                    : " --file-filter='Level packs (*.dat, *.ccl) | *.dat *.DAT *.ccl *.CCL' --file-filter='All files | *'");
    if (has("kdialog"))
        return "kdialog" + attachArg("kdialog", xid) + " --title " + q(rom ? "Load ROM" : "Load Level Pack") + " --getopenfilename " + q(dir) + " " +
               q(rom ? "*.lnx *.LNX|Lynx ROM" : "*.dat *.DAT *.ccl *.CCL|Level packs");
    return "";
}

bool App::startNativeDialog(int purpose, const std::string& startDir) {
    unsigned long xid = win_ ? windowX11Id(win_) : 0;
    std::string cmd = nativeDialogCommand(purpose == CmdLoadRom, startDir, xid);
    if (cmd.empty()) return false;
    int fds[2];
    if (pipe(fds) != 0) return false;
    pid_t pid = fork();
    if (pid < 0) { close(fds[0]); close(fds[1]); return false; }
    if (pid == 0) {                                   // child: the dialog, its answer on stdout
        dup2(fds[1], 1); close(fds[0]); close(fds[1]);
        int devnull = open("/dev/null", O_WRONLY); if (devnull >= 0) { dup2(devnull, 2); close(devnull); }
        execl("/bin/sh", "sh", "-c", cmd.c_str(), static_cast<char*>(nullptr));
        _exit(127);
    }
    close(fds[1]);
    fcntl(fds[0], F_SETFL, fcntl(fds[0], F_GETFL) | O_NONBLOCK);
    dialogPid_ = pid; dialogFd_ = fds[0]; dialogOut_.clear(); browserPurpose_ = purpose;
    modal_ = Modal::Waiting;
    return true;
}

void App::pollNativeDialog() {
    if (dialogPid_ < 0) return;
    char buf[1024];
    for (;;) { ssize_t n = read(dialogFd_, buf, sizeof buf); if (n > 0) dialogOut_.append(buf, static_cast<size_t>(n)); else break; }
    int status = 0;
    pid_t r = waitpid(dialogPid_, &status, WNOHANG);
    if (r == 0) return;                               // still open
    for (;;) { ssize_t n = read(dialogFd_, buf, sizeof buf); if (n > 0) dialogOut_.append(buf, static_cast<size_t>(n)); else break; }
    close(dialogFd_); dialogFd_ = -1; dialogPid_ = -1;
    if (modal_ == Modal::Waiting) modal_ = Modal::None;
    if (win_) SDL_RaiseWindow(win_);                  // back to the game once the dialog is gone
    std::string chosen = dialogOut_;
    while (!chosen.empty() && (chosen.back() == '\n' || chosen.back() == '\r')) chosen.pop_back();
    if (r < 0 || !WIFEXITED(status) || WEXITSTATUS(status) == 127) {   // the tool would not start: use ours
        browseTo(lastDir_.empty() ? (std::getenv("HOME") ? std::getenv("HOME") : ".") : lastDir_);
        modal_ = Modal::Browser;
        return;
    }
    if (chosen.empty()) return;                       // cancelled
    lastDir_ = std::filesystem::path(chosen).parent_path().string(); saveSettings();
    if (browserPurpose_ == CmdLoadRom) loadRomFile(chosen); else loadPackFile(chosen);
}

void App::cancelNativeDialog() {
    if (dialogPid_ < 0) return;
    kill(dialogPid_, SIGTERM);
    waitpid(dialogPid_, nullptr, 0);
    close(dialogFd_); dialogFd_ = -1; dialogPid_ = -1;
    if (modal_ == Modal::Waiting) modal_ = Modal::None;
}

void App::openFile(int purpose) {
    browserPurpose_ = purpose;
    std::string start = lastDir_;
    if (start.empty()) { const char* h = std::getenv("HOME"); start = h ? h : "."; }
    SDL_CaptureMouse(SDL_FALSE);
    if (opt_.nativeDialogs && startNativeDialog(purpose, start)) return;
    browseTo(start);
    modal_ = Modal::Browser;
}

void App::browseTo(const std::string& dir) {
    namespace fs = std::filesystem;
    std::error_code ec;
    fs::path p = fs::weakly_canonical(fs::path(dir), ec);
    if (ec || !fs::is_directory(p, ec)) p = fs::current_path(ec);
    std::vector<Entry> dirs, files;
    for (fs::directory_iterator it(p, fs::directory_options::skip_permission_denied, ec), end; !ec && it != end; it.increment(ec)) {
        std::string name = it->path().filename().string();
        if (name.empty() || name[0] == '.') continue;
        std::error_code e2;
        if (it->is_directory(e2)) dirs.push_back({name, true});
        else {
            std::string x = lowerExt(name);
            bool ok = browserPurpose_ == CmdLoadRom ? (x == "lnx" || x == "lyx") : (x == "dat" || x == "ccl");
            if (ok) files.push_back({name, false});
        }
    }
    auto byName = [](const Entry& a, const Entry& b) { return a.name < b.name; };
    std::sort(dirs.begin(), dirs.end(), byName); std::sort(files.begin(), files.end(), byName);
    entries_.clear();
    if (p.has_parent_path() && p != p.root_path()) entries_.push_back({"..", true});
    entries_.insert(entries_.end(), dirs.begin(), dirs.end());
    entries_.insert(entries_.end(), files.begin(), files.end());
    browserDir_ = p.string();
    browserSel_ = entries_.size() > 1 && entries_[0].name == ".." ? 1 : 0;
    browserTop_ = 0;
}

void App::browserActivate() {
    if (browserSel_ < 0 || browserSel_ >= static_cast<int>(entries_.size())) return;
    const Entry e = entries_[browserSel_];
    namespace fs = std::filesystem;
    if (e.dir) { browseTo(e.name == ".." ? fs::path(browserDir_).parent_path().string() : (fs::path(browserDir_) / e.name).string()); return; }
    std::string path = (fs::path(browserDir_) / e.name).string();
    modal_ = Modal::None;
    lastDir_ = browserDir_; saveSettings();
    if (browserPurpose_ == CmdLoadRom) loadRomFile(path); else loadPackFile(path);
}

// Ctrl+N / Ctrl+P: next / previous playable level, wrapping around (skips gaps and the cartridge end marker).
void App::cycleLevel(int dir) {
    int n = maxLevel(); if (n <= 0) return;
    int cur = level_;
    for (int k = 1; k <= n; ++k) {
        int c = ((cur - 1 + dir * k) % n + n) % n + 1;
        const LevelData* L = set_.find(c);
        if (L && !L->endMarker) {
            replaying_ = false; attempts_ = 0; skipCounter_ = 10; held_ = 0;
            startLevel(c);
            return;
        }
    }
}

void App::acceptLevelDialog() {
    if (levelInput_.empty()) { dialogError_ = "Type a level number"; return; }
    int n = std::atoi(levelInput_.c_str());
    const LevelData* L = set_.find(n);
    if (!L) { dialogError_ = "No level " + std::to_string(n) + " in this set"; return; }
    if (L->endMarker) { dialogError_ = "Level " + std::to_string(n) + " is the cartridge's end marker"; return; }
    modal_ = Modal::None;
    replaying_ = false; attempts_ = 0; skipCounter_ = 10; held_ = 0;
    startLevel(n);
}

void App::runCommand(int cmd) {
    modal_ = Modal::None; menuOpen_ = -1; held_ = 0;
    switch (cmd) {
    case CmdLoadRom: openFile(CmdLoadRom); break;
    case CmdLoadPack: openFile(CmdLoadPack); break;
    case CmdQuit: quit_ = true; break;
    case CmdSelectLevel:
        levelInput_.clear(); dialogError_.clear();
        modal_ = Modal::LevelDialog;
        break;
    case CmdToggleMusic: musicOn_ = !musicOn_; restartMusic_ = true; saveSettings(); break;
    case CmdToggleSfx: sfxOn_ = !sfxOn_; if (!sfxOn_) { synth_.stopAllSfx(); loopHandle_ = 0; loopId_ = 0; } saveSettings(); break;
    case CmdToggleStep: stepMode_ = !stepMode_; stepActive_ = stepQueued_ = false; held_ = 0; heldSpace_ = heldB_ = false; saveSettings(); break;   // undo history is kept
    case CmdToggleHelmet: helmet_ = !helmet_; if (game_) game_->setHelmet(helmet_); saveSettings(); break;
    case CmdInventory: openInventory(); break;
    case CmdNextLevel: cycleLevel(+1); break;
    case CmdPrevLevel: cycleLevel(-1); break;
    case CmdShowMoves: movesCopied_ = false; modal_ = Modal::Moves; break;
    }
}

// Returns true when the key was used by the menus / dialogs (or opened them).
bool App::onModalKey(SDL_Keycode k, Uint16 mod) {
    const bool ctrl = mod & KMOD_CTRL, shift = mod & KMOD_SHIFT;
    if (modal_ == Modal::None) {
        if (ctrl && k == SDLK_o) { runCommand(shift ? CmdLoadRom : CmdLoadPack); return true; }
        if (ctrl && k == SDLK_q) { runCommand(CmdQuit); return true; }
        if (ctrl && k == SDLK_g) { runCommand(CmdSelectLevel); return true; }
        if (ctrl && k == SDLK_i) { runCommand(CmdInventory); return true; }
        if (ctrl && (k == SDLK_p || k == SDLK_n)) { cycleLevel(k == SDLK_n ? +1 : -1); return true; }
        if (ctrl && k == SDLK_m) { runCommand(CmdShowMoves); return true; }
        if (k == SDLK_F10) { modal_ = Modal::Menu; menuOpen_ = 0; menuHover_ = 0; return true; }
        return false;
    }
    bool confirm = (k == SDLK_RETURN || k == SDLK_KP_ENTER);
    switch (modal_) {
    case Modal::Menu: {
        auto& items = menus_[menuOpen_].items;
        int n = static_cast<int>(items.size());
        auto stepHover = [&](int dlt) { for (int j = 0; j < n; ++j) { menuHover_ = (menuHover_ + dlt + n) % n; if (items[menuHover_].label) break; } };
        if (k == SDLK_ESCAPE || k == SDLK_F10) { modal_ = Modal::None; menuOpen_ = -1; }
        else if (k == SDLK_DOWN) stepHover(+1);
        else if (k == SDLK_UP) stepHover(-1);
        else if (k == SDLK_LEFT || k == SDLK_RIGHT) {
            int m = static_cast<int>(menus_.size());
            menuOpen_ = (menuOpen_ + (k == SDLK_RIGHT ? 1 : -1) + m) % m; menuHover_ = 0;
        }
        else if (confirm || k == SDLK_SPACE) { if (menuHover_ >= 0 && menuHover_ < n && items[menuHover_].label) runCommand(items[menuHover_].cmd); }
        return true;
    }
    case Modal::LevelDialog:
        if (k == SDLK_ESCAPE) modal_ = Modal::None;
        else if (confirm) acceptLevelDialog();
        else if (k == SDLK_BACKSPACE) { if (!levelInput_.empty()) levelInput_.pop_back(); dialogError_.clear(); }
        else {
            int digit = (k >= SDLK_0 && k <= SDLK_9) ? int(k - SDLK_0) : (k >= SDLK_KP_1 && k <= SDLK_KP_9) ? int(k - SDLK_KP_1 + 1) : k == SDLK_KP_0 ? 0 : -1;
            if (digit >= 0 && levelInput_.size() < 4) { levelInput_ += char('0' + digit); dialogError_.clear(); }
        }
        return true;
    case Modal::Message:
        if (confirm || k == SDLK_ESCAPE || k == SDLK_SPACE) modal_ = Modal::None;
        return true;
    case Modal::Moves:
        if (k == SDLK_ESCAPE || confirm || k == SDLK_SPACE) modal_ = Modal::None;
        else if (k == SDLK_c) { SDL_SetClipboardText(moves_.c_str()); movesCopied_ = true; }
        return true;
    case Modal::Inventory: {
        int digit = (k >= SDLK_0 && k <= SDLK_9) ? int(k - SDLK_0) : (k >= SDLK_KP_1 && k <= SDLK_KP_9) ? int(k - SDLK_KP_1 + 1) : k == SDLK_KP_0 ? 0 : -1;
        if (k == SDLK_ESCAPE) modal_ = Modal::None;
        else if (confirm) applyInventory();
        else if (k == SDLK_UP) { invRow_ = (invRow_ + 7) % 8; invTyped_ = false; }
        else if (k == SDLK_DOWN || k == SDLK_TAB) { invRow_ = (invRow_ + 1) % 8; invTyped_ = false; }
        else if (k == SDLK_LEFT) invAdjust(invRow_, -1);
        else if (k == SDLK_RIGHT) invAdjust(invRow_, +1);
        else if (k == SDLK_PAGEDOWN) invAdjust(invRow_, -10);
        else if (k == SDLK_PAGEUP) invAdjust(invRow_, +10);
        else if (k == SDLK_SPACE && invRow_ >= 4) invAdjust(invRow_, 0);
        else if (k == SDLK_BACKSPACE && invRow_ < 4) { inv_[invRow_] /= 10; invTyped_ = true; }
        else if (digit >= 0 && invRow_ < 4) {   // typing a number replaces the count
            int v = invTyped_ ? inv_[invRow_] * 10 + digit : digit;
            inv_[invRow_] = std::min(v, 255); invTyped_ = true;
        }
        return true;
    }
    case Modal::Waiting:
        if (k == SDLK_ESCAPE) cancelNativeDialog();
        return true;
    case Modal::Browser: {
        int n = static_cast<int>(entries_.size());
        const int rows = (kScreenH - 28 - 104 - 8) / 22;
        if (k == SDLK_ESCAPE) modal_ = Modal::None;
        else if (k == SDLK_DOWN) browserSel_ = std::min(n - 1, browserSel_ + 1);
        else if (k == SDLK_UP) browserSel_ = std::max(0, browserSel_ - 1);
        else if (k == SDLK_PAGEDOWN) browserSel_ = std::min(n - 1, browserSel_ + rows);
        else if (k == SDLK_PAGEUP) browserSel_ = std::max(0, browserSel_ - rows);
        else if (k == SDLK_HOME) browserSel_ = 0;
        else if (k == SDLK_END) browserSel_ = n - 1;
        else if (k == SDLK_BACKSPACE) browseTo(std::filesystem::path(browserDir_).parent_path().string());
        else if (confirm) browserActivate();
        else if (k >= SDLK_a && k <= SDLK_z) {            // jump to the next entry starting with that letter
            for (int j = 1; j <= n; ++j) {
                int q = (browserSel_ + j) % n;
                if (!entries_[q].name.empty() && std::tolower(static_cast<unsigned char>(entries_[q].name[0])) == 'a' + (k - SDLK_a)) { browserSel_ = q; break; }
            }
        }
        if (browserSel_ < browserTop_) browserTop_ = browserSel_;
        if (browserSel_ >= browserTop_ + rows) browserTop_ = browserSel_ - rows + 1;
        return true;
    }
    default: return false;
    }
}

void App::onMouse(const SDL_Event& e) {
    int mx = 0, my = 0;
    if (e.type == SDL_MOUSEMOTION) { mx = e.motion.x; my = e.motion.y; }
    else if (e.type == SDL_MOUSEBUTTONDOWN) { mx = e.button.x; my = e.button.y; }
    SDL_Point pt{mx, my};
    auto in = [&](SDL_Rect r) { return SDL_PointInRect(&pt, &r) == SDL_TRUE; };
    const int mid = kScreenW / 2;
    if (e.type == SDL_MOUSEWHEEL) {
        if (modal_ == Modal::Browser) {
            browserTop_ = std::max(0, std::min(static_cast<int>(entries_.size()) - 1, browserTop_ - e.wheel.y * 3));
        }
        return;
    }
    if (modal_ == Modal::Waiting) return;          // the native dialog has the user's attention
    // menu bar titles
    if (my < kMenuH && (e.type == SDL_MOUSEBUTTONDOWN || modal_ == Modal::Menu)) {
        for (int m = 0; m < static_cast<int>(menus_.size()); ++m)
            if (in(menuTitleRect(m))) {
                if (e.type == SDL_MOUSEBUTTONDOWN) {
                    if (modal_ == Modal::Menu && menuOpen_ == m) { modal_ = Modal::None; menuOpen_ = -1; }
                    else if (modal_ == Modal::None || modal_ == Modal::Menu) { modal_ = Modal::Menu; menuOpen_ = m; menuHover_ = -1; held_ = 0; }
                } else if (modal_ == Modal::Menu) { menuOpen_ = m; }
                return;
            }
        if (e.type == SDL_MOUSEBUTTONDOWN && modal_ == Modal::Menu) { modal_ = Modal::None; menuOpen_ = -1; }
        return;
    }
    switch (modal_) {
    case Modal::Waiting: return;
    case Modal::Menu: {
        menuHover_ = -1;
        for (int k = 0; k < static_cast<int>(menus_[menuOpen_].items.size()); ++k)
            if (menus_[menuOpen_].items[k].label && in(menuItemRect(menuOpen_, k))) menuHover_ = k;
        if (e.type == SDL_MOUSEBUTTONDOWN) {
            if (menuHover_ >= 0) runCommand(menus_[menuOpen_].items[menuHover_].cmd);
            else if (!in(dropRect(menuOpen_))) { modal_ = Modal::None; menuOpen_ = -1; }
        }
        return;
    }
    case Modal::LevelDialog:
        if (e.type != SDL_MOUSEBUTTONDOWN) return;
        { int by = kMenuH + 110 + 150;
          if (in(SDL_Rect{mid - 120, by, 110, 30})) acceptLevelDialog();
          else if (in(SDL_Rect{mid + 10, by, 110, 30})) modal_ = Modal::None; }
        return;
    case Modal::Message:
        if (e.type == SDL_MOUSEBUTTONDOWN && in(SDL_Rect{mid - 55, kMenuH + 140 + 90, 110, 30})) modal_ = Modal::None;
        return;
    case Modal::Moves: {
        if (e.type != SDL_MOUSEBUTTONDOWN) return;
        SDL_Rect b{mid - 280, kMenuH + 40, 560, 350};
        if (in(SDL_Rect{mid - 120, b.y + b.h - 44, 110, 30})) { SDL_SetClipboardText(moves_.c_str()); movesCopied_ = true; }
        else if (in(SDL_Rect{mid + 10, b.y + b.h - 44, 110, 30})) modal_ = Modal::None;
        return;
    }
    case Modal::Inventory: {
        if (e.type != SDL_MOUSEBUTTONDOWN) return;
        SDL_Rect b = invBox();
        for (int r = 0; r < 8; ++r) {
            SDL_Rect rr = invRowRect(r);
            if (!in(rr)) continue;
            invRow_ = r; invTyped_ = false;
            if (r >= 4) invAdjust(r, 0);
            else if (in(SDL_Rect{rr.x + rr.w - 150, rr.y, 40, rr.h})) invAdjust(r, -1);
            else if (in(SDL_Rect{rr.x + rr.w - 40, rr.y, 40, rr.h})) invAdjust(r, +1);
            return;
        }
        if (in(SDL_Rect{mid - 120, b.y + b.h - 44, 110, 30})) applyInventory();
        else if (in(SDL_Rect{mid + 10, b.y + b.h - 44, 110, 30})) modal_ = Modal::None;
        return;
    }
    case Modal::Browser: {
        if (e.type != SDL_MOUSEBUTTONDOWN) return;
        SDL_Rect b{30, kMenuH + 14, kScreenW - 60, kScreenH - 28};
        SDL_Rect list{b.x + 10, b.y + 56, b.w - 20, b.h - 104};
        if (in(SDL_Rect{b.x + b.w - 250, b.y + b.h - 42, 110, 30})) { browserActivate(); return; }
        if (in(SDL_Rect{b.x + b.w - 130, b.y + b.h - 42, 110, 30})) { modal_ = Modal::None; return; }
        if (in(list)) {
            int row = (my - list.y - 4) / 22, k = browserTop_ + row;
            if (k >= 0 && k < static_cast<int>(entries_.size())) {
                Uint32 now = SDL_GetTicks();
                bool dbl = (k == lastClickRow_ && now - lastClick_ < 400);
                browserSel_ = k; lastClickRow_ = k; lastClick_ = now;
                if (dbl) browserActivate();
            }
        }
        return;
    }
    case Modal::None:
        if (e.type == SDL_MOUSEBUTTONDOWN && e.button.button == SDL_BUTTON_LEFT && game_ && game_->outOfSync() &&
            (screen_ == Screen::Play || screen_ == Screen::Died)) {
            SDL_Point gp{mx, my - kMenuH};
            SDL_Rect q = desyncButton();
            if (SDL_PointInRect(&gp, &q)) { desyncInfo_ = !desyncInfo_; return; }
        }
        if (e.type == SDL_MOUSEBUTTONDOWN && e.button.button == SDL_BUTTON_LEFT && screen_ == Screen::Title) {
            SDL_Point gp{mx, my - kMenuH};                       // game-area coordinates
            for (int k = 0; k < 2; ++k) {
                SDL_Rect r = modeBox(k); r.w = 260;              // the label is clickable too
                if (SDL_PointInRect(&gp, &r)) setExtended(k == 1);
            }
        }
        return;
    }
}

// ---------------------------------------------------------------- main loop
static std::string configBase() {
    const char* xdg = std::getenv("XDG_CONFIG_HOME");
    const char* home = std::getenv("HOME");
    return xdg && *xdg ? xdg : home ? std::string(home) + "/.config" : ".";
}

std::string App::settingsPath() { return configBase() + "/ponderpuzzlers/settings.txt"; }

void App::loadSettings() {
    std::ifstream f(settingsPath()); std::string line;
    if (!f) f.open(configBase() + "/chiplynx/settings.txt");   // settings saved under the old working title
    while (std::getline(f, line)) {
        if (line == "mode=extended") extended_ = true;
        else if (line == "mode=strict") extended_ = false;
        else if (line.rfind("lastdir=", 0) == 0) lastDir_ = line.substr(8);
        else if (line == "music=0") musicOn_ = false;
        else if (line == "sfx=0") sfxOn_ = false;
        else if (line == "stepmode=1") stepMode_ = true;
        else if (line == "helmet=1") helmet_ = true;
    }
}

void App::saveSettings() const {
    std::error_code ec;
    std::filesystem::create_directories(std::filesystem::path(settingsPath()).parent_path(), ec);
    std::ofstream f(settingsPath());
    if (f) f << "mode=" << (extended_ ? "extended" : "strict") << "\n" << "lastdir=" << lastDir_ << "\n"
               << "music=" << (musicOn_ ? 1 : 0) << "\n" << "sfx=" << (sfxOn_ ? 1 : 0) << "\n"
               << "stepmode=" << (stepMode_ ? 1 : 0) << "\n" << "helmet=" << (helmet_ ? 1 : 0) << "\n";
}

void App::loadSet() {
    DatOptions opt; opt.extended = extended_;
    LevelSet s;
    if (!opt_.rom.empty() && opt_.levels.empty()) {
        Rom rom(opt_.rom);
        s = cartridgeLevels(rom);          // the cartridge's own levels play the same in both modes
        passwords_ = generatePasswords();
        strictAltered_ = 0;
    } else {
        DatReport strictRep;
        DatOptions so;                    // count what strict mode has to change, for the title screen note
        if (opt_.levels.empty()) {        // built-in original level set: no files needed
            std::vector<uint8_t> bytes(kBuiltinLevels, kBuiltinLevels + kBuiltinLevelsSize);
            s = loadDatBytes(bytes, "Pip's First Steps", nullptr, opt);
            loadDatBytes(bytes, "", &strictRep, so);
        } else {
            s = loadDat(opt_.levels, nullptr, opt);
            loadDat(opt_.levels, &strictRep, so);
        }
        std::vector<int> altered;
        for (auto& w : strictRep.warnings) {
            int n = 0;
            if (std::sscanf(w.c_str(), "level %d", &n) == 1 && std::find(altered.begin(), altered.end(), n) == altered.end()) altered.push_back(n);
        }
        strictAltered_ = static_cast<int>(altered.size());
        passwords_.clear();
        for (auto& L : s.levels) passwords_.push_back(L.password.empty() ? "----" : L.password);
    }
    set_ = std::move(s);
}

void App::setExtended(bool on) {
    if (on == extended_) return;
    extended_ = on;
    try { loadSet(); } catch (const std::exception& e) { std::fprintf(stderr, "%s\n", e.what()); }
    saveSettings();
}

int App::run() {
    loadSettings();
    if (opt_.mode >= 0) extended_ = opt_.mode == 1;
    try {
        loadSet();
    } catch (const std::exception& e) {
        std::fprintf(stderr, "Could not load levels: %s\n"
                     "Usage: ponderpuzzlers [--levels set.dat | --rom cartridge.lnx]\n", e.what());
        return 1;
    }
    if (set_.levels.empty()) { std::fprintf(stderr, "level set is empty\n"); return 1; }
    bool headless = !opt_.shot.empty();
    if (headless) SDL_SetHint(SDL_HINT_VIDEODRIVER, "dummy");
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS) != 0) { std::fprintf(stderr, "SDL: %s\n", SDL_GetError()); return 1; }
    win_ = SDL_CreateWindow("Ponder Puzzlers", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, kScreenW * opt_.scale, kWinH * opt_.scale,
                            SDL_WINDOW_RESIZABLE | (headless ? SDL_WINDOW_HIDDEN : 0));
    ren_ = SDL_CreateRenderer(win_, -1, headless ? SDL_RENDERER_SOFTWARE : (SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC));
    if (!ren_) ren_ = SDL_CreateRenderer(win_, -1, SDL_RENDERER_SOFTWARE);
    SDL_RenderSetLogicalSize(ren_, kScreenW, kWinH);
    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "1");
    if (!assets_.load(ren_, opt_.assets)) { std::fprintf(stderr, "Could not load assets from %s\n", opt_.assets.c_str()); return 1; }
    if (!headless) initAudio();

    if (!opt_.hacks.empty()) { stepMode_ = opt_.hacks.find("step") != std::string::npos; helmet_ = opt_.hacks.find("helmet") != std::string::npos; }
    if (opt_.level > 0) { level_ = opt_.level; startLevel(level_); }
    {   // headless key script
        static const std::map<std::string, SDL_Keycode> kKeys = {{"up", SDLK_UP}, {"down", SDLK_DOWN}, {"left", SDLK_LEFT},
            {"right", SDLK_RIGHT}, {"space", SDLK_SPACE}, {"enter", SDLK_RETURN}, {"b", SDLK_b}, {"backspace", SDLK_BACKSPACE}, {"r", SDLK_r}};
        std::stringstream ss(opt_.script); std::string item;
        while (std::getline(ss, item, ',')) {
            auto c = item.find(':'); if (c == std::string::npos) continue;
            std::string key = item.substr(c + 1), name = (key[0] == '+' || key[0] == '-') ? key.substr(1) : key;   // +key down, -key up
            if (kKeys.count(name)) script_.push_back({std::stoi(item.substr(0, c)), key});
        }
    }
    if (!opt_.uiTest.empty()) {                    // headless screenshots of the menus and dialogs
        if (opt_.uiTest == "menu-file") { modal_ = Modal::Menu; menuOpen_ = 0; menuHover_ = 1; }
        else if (opt_.uiTest == "menu-level") { modal_ = Modal::Menu; menuOpen_ = 1; menuHover_ = 0; }
        else if (opt_.uiTest == "menu-hacks") { modal_ = Modal::Menu; menuOpen_ = 3; menuHover_ = 1; }
        else if (opt_.uiTest == "next" || opt_.uiTest == "prev") cycleLevel(opt_.uiTest == "next" ? +1 : -1);
        else if (opt_.uiTest == "inventory") { openInventory(); inv_[0] = 3; inv_[6] = 1; invRow_ = 6; }
        else if (opt_.uiTest == "level-dialog") { runCommand(CmdSelectLevel); levelInput_ = "12"; }
        else if (opt_.uiTest == "level-error") { runCommand(CmdSelectLevel); levelInput_ = "145"; acceptLevelDialog(); }
        else if (opt_.uiTest == "browser") { opt_.nativeDialogs = false; openFile(CmdLoadPack); }
        else if (opt_.uiTest == "native") openFile(CmdLoadPack);
        else if (opt_.uiTest.rfind("pack:", 0) == 0) loadPackFile(opt_.uiTest.substr(5));
        else if (opt_.uiTest.rfind("rom:", 0) == 0) loadRomFile(opt_.uiTest.substr(4));
        else if (opt_.uiTest.rfind("select:", 0) == 0) { runCommand(CmdSelectLevel); levelInput_ = opt_.uiTest.substr(7); acceptLevelDialog(); }
        else if (opt_.uiTest == "outofsync" && game_) game_->debugMarkOutOfSync(1);
        else if (opt_.uiTest == "outofsync2" && game_) game_->debugMarkOutOfSync(2);
        else if (opt_.uiTest == "outofsync3" && game_) game_->debugMarkOutOfSync(3);
        else if (opt_.uiTest.rfind("soundnote:", 0) == 0 && game_) game_->debugMarkSoundGlitch(static_cast<uint8_t>(std::stoi(opt_.uiTest.substr(10), nullptr, 16)));
        else if (opt_.uiTest.rfind("desync-info:", 0) == 0 && game_) {   // desync-info:WHAT (1-7)
            int what = std::stoi(opt_.uiTest.substr(12));
            game_->debugMarkOutOfSync(what == 7 ? 3 : what == 6 ? 2 : 1, what); desyncInfo_ = true;
        }
        else if (opt_.uiTest == "browse-enter") { opt_.nativeDialogs = false; openFile(CmdLoadPack); onModalKey(SDLK_END, 0); onModalKey(SDLK_UP, 0); onModalKey(SDLK_UP, 0); onModalKey(SDLK_RETURN, 0); }
    }
    if (!opt_.replay.empty()) {
        TwsFile tws = loadTws(opt_.replay);
        for (auto& s : tws.solutions) if (s.level == level_) {
            for (auto& m : s.moves) replayInput_[m.tick] |= twsDirToMask(m.dir);
            if (tws.ruleset == 1) globals_.randomForce = twsSlideToR(s.slide);   // the solution's initial random-floor direction
        }
        replaying_ = true;
        if (screen_ != Screen::Play) startLevel(level_);
    }

    Uint64 freq = SDL_GetPerformanceFrequency(), last = SDL_GetPerformanceCounter();
    double acc = 0;
    bool quit = false;
    while (!quit) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            if (e.type == SDL_QUIT) quit = true;
            else if (e.type == SDL_KEYDOWN && (!e.key.repeat || modal_ != Modal::None)) onKey(e.key.keysym.sym, true);
            else if (e.type == SDL_KEYUP) onKey(e.key.keysym.sym, false);
            else if (e.type == SDL_MOUSEBUTTONDOWN || e.type == SDL_MOUSEMOTION || e.type == SDL_MOUSEWHEEL) onMouse(e);
        }
        pollNativeDialog();
        updateAudio();
        if (quit_) quit = true;
        if (headless) {
            for (auto& [f, key] : script_) if (f == frameTicks_) {
                static const std::map<std::string, SDL_Keycode> kKeys = {{"up", SDLK_UP}, {"down", SDLK_DOWN}, {"left", SDLK_LEFT},
                    {"right", SDLK_RIGHT}, {"space", SDLK_SPACE}, {"enter", SDLK_RETURN}, {"b", SDLK_b}, {"backspace", SDLK_BACKSPACE}, {"r", SDLK_r}};
                bool dn = key[0] != '-', up = key[0] != '+';
                SDL_Keycode kc = kKeys.at(up && dn ? key : key.substr(1));
                if (dn) onKey(kc, true);
                if (up) onKey(kc, false);
            }
            update();
            if (std::getenv("PONDER_STEP_LOG") && game_)
                std::fprintf(stderr, "F %d x %d y %d state %02x time %d screen %d undo %zu level %d\n", frameTicks_, game_->objX(0), game_->objY(0),
                             game_->objState(0), game_->timeLeft(), int(screen_), undo_.size(), level_);
            if (++frameTicks_ >= opt_.shotTicks) {
                if (opt_.uiTest == "moves") modal_ = Modal::Moves;
                if (std::getenv("PONDER_STEP_LOG")) std::fprintf(stderr, "MOVES %s\nTICKS %ld\n", moves_.c_str(), gameTicks_);
                render(1.0);
                SDL_Surface* s = SDL_CreateRGBSurfaceWithFormat(0, kScreenW * opt_.scale, kWinH * opt_.scale, 32, SDL_PIXELFORMAT_ARGB8888);
                SDL_RenderReadPixels(ren_, nullptr, SDL_PIXELFORMAT_ARGB8888, s->pixels, s->pitch);
                SDL_SaveBMP(s, opt_.shot.c_str());
                SDL_FreeSurface(s);
                quit = true;
            }
            continue;
        }
        Uint64 now = SDL_GetPerformanceCounter();
        acc += double(now - last) / freq; last = now;
        if (acc > 0.25) acc = 0.25;
        while (acc >= kTickSeconds) { update(); acc -= kTickSeconds; }
        render(acc / kTickSeconds);
    }
    cancelNativeDialog();
    if (audioDev_) SDL_CloseAudioDevice(audioDev_);
    SDL_DestroyRenderer(ren_); SDL_DestroyWindow(win_); SDL_Quit();
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    Options o;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto next = [&]() { return i + 1 < argc ? std::string(argv[++i]) : std::string(); };
        if (a == "--rom") o.rom = next();
        else if (a == "--levels") o.levels = next();
        else if (a == "--assets") o.assets = next();
        else if (a == "--level") o.level = std::stoi(next());
        else if (a == "--replay") o.replay = next();
        else if (a == "--scale") o.scale = std::stoi(next());
        else if (a == "--screenshot") o.shot = next();
        else if (a == "--ticks") o.shotTicks = std::stoi(next());
        else if (a == "--strict") o.mode = 0;
        else if (a == "--extended") o.mode = 1;
        else if (a == "--ui-test") o.uiTest = next();
        else if (a == "--script") o.script = next();
        else if (a == "--hacks") o.hacks = next();
        else if (a == "--no-native-dialogs") o.nativeDialogs = false;
        else if (a == "--help" || a == "-h") {
            std::printf("ponderpuzzlers [--levels set.dat | --rom cartridge.lnx] [--strict | --extended] [--level N]\n"
                        "         [--replay solutions.tws] [--scale 2]\n"
                        "With no --levels/--rom the built-in level set is played.\n"
                        "--strict    Strict LYNX ROM: only what the original cartridge can do (default)\n"
                        "--extended  Extended LYNX mode: as Tile World's Lynx mode (DAT wiring, all thin walls,\n"
                        "            no 128-object limit). The choice is also on the title screen and is remembered.\n");
            return 0;
        }
    }
    App app(o);
    return app.run();
}
