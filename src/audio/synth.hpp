// Small software synthesizer for the newly composed music and sound effects.
// Music and effects share one format: a "song" is a list of timed note events played by named instruments
// (see assets/audio/README.md). No SDL dependency: the game feeds the output to an SDL audio device, and
// tools/audiorender writes it to WAV files.
#pragma once
#include <array>
#include <cstdint>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

namespace audio {

enum class Wave : uint8_t { Pulse, Saw, Tri, Sine, Noise, Metal };

struct Instrument {
    std::string name;
    Wave wave = Wave::Pulse;
    float duty = 0.5f, pwm = 0.f, pwmRate = 0.f;   // pulse width, modulation depth / rate (Hz)
    float detune = 0.f, mix2 = 0.f, oct2 = 0.f;    // second oscillator: cents, level, octave offset
    float sub = 0.f;                               // sine one octave below
    float a = 0.005f, d = 0.1f, s = 0.7f, r = 0.1f; // envelope (seconds, sustain level)
    float gain = 0.5f, pan = 0.f;
    float cutoff = 18000.f, res = 0.f, fenv = 0.f, fdecay = 0.2f, keytrack = 0.f;
    float hp = 0.f;                                // high-pass cutoff (Hz), 0 = off
    float vib = 0.f, vibRate = 5.5f, vibDelay = 0.2f;
    float pslide = 0.f, pdecay = 0.05f;            // pitch starts pslide semitones away, decays exponentially
    float noiseRate = 1.f;                         // noise / metal: sample-and-hold rate factor
    float delay = 0.f, verb = 0.f;                 // effect sends
    bool mono = false;                             // a new note cuts the previous one of this instrument
};

struct Note {
    int tick;
    int inst;
    float pitch;      // MIDI note number (fractional allowed)
    int len;          // ticks
    float vel;
    float to;         // glide target (MIDI), NaN = none
};

struct Song {
    std::string name;
    float tempo = 120.f;          // beats per minute
    int tpb = 4;                  // ticks per beat
    int length = 0;               // ticks (end / loop end)
    int loop = -1;                // loop start tick, -1 = play once
    float delayBeats = 0.75f;     // echo time in beats
    float delayFeedback = 0.35f;
    std::vector<Instrument> insts;
    std::vector<Note> notes;      // sorted by tick
    double samplesPerTick(int rate) const { return rate * 60.0 / (tempo * tpb); }
};

// Parses the text format. Throws std::runtime_error.
Song parseSong(const std::string& text, const std::string& name);
Song loadSong(const std::string& path);

class Synth {
public:
    explicit Synth(int sampleRate = 48000);
    ~Synth();
    int rate() const { return rate_; }

    // Music: one song at a time, looping as the song says. nullptr stops.
    void playMusic(const Song* song);
    void stopMusic();
    // Effects: any number at once. Returns a handle (for looping effects); retriggering the same
    // effect restarts it.
    int playSfx(const Song* sfx, bool loop = false);
    void stopSfx(int handle);
    void stopAllSfx();

    void setMusicVolume(float v) { musicVol_ = v; }
    void setSfxVolume(float v) { sfxVol_ = v; }
    void setPaused(bool p) { paused_ = p; }

    // Mixes `frames` stereo frames (interleaved L/R floats).
    void render(float* out, int frames);
    std::mutex& lock() { return mtx_; }

private:
    struct Voice;
    struct Player {
        const Song* song = nullptr;
        double pos = 0;           // ticks (fractional)
        size_t next = 0;          // next note index
        bool loop = false, active = false, music = false;
        int id = 0;
    };
    void startNote(Player& p, int playerIdx, const Note& n);
    void advancePlayer(Player& p, int idx, double ticks);
    void renderVoice(Voice& v, float* l, float* r, float* dl, float* dr, float* vl, float* vr, int frames);

    int rate_;
    std::vector<Player> players_;     // 0 = music
    std::vector<std::unique_ptr<Voice>> voices_;
    int nextId_ = 1;
    float musicVol_ = 0.8f, sfxVol_ = 0.9f;
    bool paused_ = false;
    // effects bus
    std::vector<float> delayL_, delayR_; size_t delayPos_ = 0;
    struct Comb { std::vector<float> buf; size_t pos = 0; float store = 0; };
    struct Allpass { std::vector<float> buf; size_t pos = 0; };
    std::array<Comb, 8> combs_; std::array<Allpass, 4> aps_;
    uint32_t noiseSeed_ = 0x12345;
    std::mutex mtx_;
};

} // namespace audio
