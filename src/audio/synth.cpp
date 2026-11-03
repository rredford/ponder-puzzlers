#include "synth.hpp"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace audio {

static constexpr float kPi = 3.14159265358979f;

// ---------------------------------------------------------------- parsing
static void setParam(Instrument& in, const std::string& k, const std::string& v) {
    auto f = [&]() { return std::stof(v); };
    if (k == "wave") {
        in.wave = v == "pulse" ? Wave::Pulse : v == "saw" ? Wave::Saw : v == "tri" ? Wave::Tri : v == "sine" ? Wave::Sine
                : v == "noise" ? Wave::Noise : v == "metal" ? Wave::Metal : throw std::runtime_error("unknown wave " + v);
    }
    else if (k == "duty") in.duty = f(); else if (k == "pwm") in.pwm = f(); else if (k == "pwmrate") in.pwmRate = f();
    else if (k == "detune") in.detune = f(); else if (k == "mix2") in.mix2 = f(); else if (k == "oct2") in.oct2 = f();
    else if (k == "sub") in.sub = f();
    else if (k == "a") in.a = f(); else if (k == "d") in.d = f(); else if (k == "s") in.s = f(); else if (k == "r") in.r = f();
    else if (k == "gain") in.gain = f(); else if (k == "pan") in.pan = f();
    else if (k == "cutoff") in.cutoff = f(); else if (k == "res") in.res = f(); else if (k == "fenv") in.fenv = f();
    else if (k == "fdecay") in.fdecay = f(); else if (k == "keytrack") in.keytrack = f(); else if (k == "hp") in.hp = f();
    else if (k == "vib") in.vib = f(); else if (k == "vibrate") in.vibRate = f(); else if (k == "vibdelay") in.vibDelay = f();
    else if (k == "pslide") in.pslide = f(); else if (k == "pdecay") in.pdecay = f(); else if (k == "noiserate") in.noiseRate = f();
    else if (k == "delay") in.delay = f(); else if (k == "verb") in.verb = f();
    else if (k == "mono") in.mono = v == "1" || v == "true";
    else throw std::runtime_error("unknown instrument parameter " + k);
}

Song parseSong(const std::string& text, const std::string& name) {
    Song s; s.name = name;
    std::istringstream in(text);
    std::string line; int lineNo = 0;
    auto instIndex = [&](const std::string& n) {
        for (size_t i = 0; i < s.insts.size(); ++i) if (s.insts[i].name == n) return static_cast<int>(i);
        throw std::runtime_error("unknown instrument " + n);
    };
    while (std::getline(in, line)) {
        ++lineNo;
        auto hash = line.find('#'); if (hash != std::string::npos) line.erase(hash);
        std::istringstream ls(line); std::string cmd;
        if (!(ls >> cmd)) continue;
        try {
            if (cmd == "name") { std::getline(ls >> std::ws, s.name); }
            else if (cmd == "tempo") ls >> s.tempo;
            else if (cmd == "tpb") ls >> s.tpb;
            else if (cmd == "length") ls >> s.length;
            else if (cmd == "loop") ls >> s.loop;
            else if (cmd == "echo") ls >> s.delayBeats >> s.delayFeedback;
            else if (cmd == "inst") {
                Instrument ins; ls >> ins.name;
                std::string kv;
                while (ls >> kv) { auto eq = kv.find('='); if (eq == std::string::npos) throw std::runtime_error("bad " + kv); setParam(ins, kv.substr(0, eq), kv.substr(eq + 1)); }
                s.insts.push_back(ins);
            } else if (cmd == "n") {
                Note n; std::string inst; ls >> n.tick >> inst >> n.pitch >> n.len >> n.vel;
                n.inst = instIndex(inst); n.to = NAN;
                std::string kv;
                while (ls >> kv) if (kv.rfind("to=", 0) == 0) n.to = std::stof(kv.substr(3));
                if (!ls.eof() && ls.fail()) throw std::runtime_error("bad note");
                s.notes.push_back(n);
            } else throw std::runtime_error("unknown command " + cmd);
        } catch (const std::exception& e) {
            throw std::runtime_error(name + ":" + std::to_string(lineNo) + ": " + e.what());
        }
    }
    std::stable_sort(s.notes.begin(), s.notes.end(), [](const Note& a, const Note& b) { return a.tick < b.tick; });
    if (s.length <= 0) for (auto& n : s.notes) s.length = std::max(s.length, n.tick + n.len);
    return s;
}

Song loadSong(const std::string& path) {
    std::ifstream f(path);
    if (!f) throw std::runtime_error("cannot open " + path);
    std::stringstream ss; ss << f.rdbuf();
    auto slash = path.find_last_of('/');
    return parseSong(ss.str(), slash == std::string::npos ? path : path.substr(slash + 1));
}

// ---------------------------------------------------------------- voices
struct Synth::Voice {
    const Instrument* in = nullptr;
    int player = -1, playerId = 0, inst = -1;
    bool music = false, active = false, released = false;
    float pitch = 60, to = NAN, vel = 1;
    double t = 0;                 // seconds since start
    double gate = 0;              // seconds until release
    double glideTime = 0;
    float env = 0, relStart = 0; double relT = 0; float relLen = 0.1f;
    double ph1 = 0, ph2 = 0, phs = 0;
    float ic1 = 0, ic2 = 0, hpY = 0, hpX = 0;
    float g = 0, k = 2; int coefCountdown = 0;
    uint32_t lfsr = 0x7FFF; double nph = 0; float nval = 0;
    float panL = 0.7f, panR = 0.7f;
};

Synth::Synth(int sampleRate) : rate_(sampleRate) {
    players_.resize(1);
    players_[0].music = true;
    for (int i = 0; i < 48; ++i) voices_.push_back(std::make_unique<Voice>());
    delayL_.assign(rate_ * 2, 0.f); delayR_.assign(rate_ * 2, 0.f);
    const int combLen[4] = {1116, 1188, 1277, 1356}, apLen[2] = {556, 441};
    float scale = rate_ / 44100.f;
    for (int i = 0; i < 8; ++i) combs_[i].buf.assign(static_cast<size_t>((combLen[i & 3] + (i >= 4 ? 23 : 0)) * scale), 0.f);
    for (int i = 0; i < 4; ++i) aps_[i].buf.assign(static_cast<size_t>((apLen[i & 1] + (i >= 2 ? 23 : 0)) * scale), 0.f);
}

Synth::~Synth() = default;

void Synth::playMusic(const Song* song) {
    std::lock_guard<std::mutex> g(mtx_);
    for (auto& v : voices_) if (v->active && v->music && !v->released) { v->released = true; v->relStart = v->env; v->relT = 0; v->relLen = 0.03f; }
    Player& p = players_[0];
    p = Player{}; p.music = true;
    if (!song) return;
    p.song = song; p.loop = song->loop >= 0; p.active = true; p.id = nextId_++;
    if (song->notes.empty()) p.active = false;
}

void Synth::stopMusic() { playMusic(nullptr); }

int Synth::playSfx(const Song* sfx, bool loop) {
    if (!sfx) return 0;
    std::lock_guard<std::mutex> g(mtx_);
    // retriggering an effect restarts it
    for (size_t i = 1; i < players_.size(); ++i)
        if (players_[i].active && players_[i].song == sfx) {
            for (auto& v : voices_) if (v->active && v->playerId == players_[i].id && !v->released) { v->released = true; v->relStart = v->env; v->relT = 0; v->relLen = 0.01f; }
            players_[i].active = false;
        }
    size_t slot = 1;
    while (slot < players_.size() && players_[slot].active) ++slot;
    if (slot == players_.size()) players_.emplace_back();
    Player& p = players_[slot];
    p = Player{}; p.song = sfx; p.loop = loop; p.active = true; p.id = nextId_++;
    return p.id;
}

void Synth::stopSfx(int handle) {
    if (!handle) return;
    std::lock_guard<std::mutex> g(mtx_);
    for (size_t i = 1; i < players_.size(); ++i) if (players_[i].active && players_[i].id == handle) players_[i].active = false;
    for (auto& v : voices_) if (v->active && v->playerId == handle && !v->released) { v->released = true; v->relStart = v->env; v->relT = 0; v->relLen = 0.05f; }
}

void Synth::stopAllSfx() {
    std::lock_guard<std::mutex> g(mtx_);
    for (size_t i = 1; i < players_.size(); ++i) players_[i].active = false;
    for (auto& v : voices_) if (v->active && !v->music && !v->released) { v->released = true; v->relStart = v->env; v->relT = 0; v->relLen = 0.03f; }
}

void Synth::startNote(Player& p, int playerIdx, const Note& n) {
    const Instrument& in = p.song->insts[n.inst];
    if (in.mono)
        for (auto& v : voices_)
            if (v->active && v->playerId == p.id && v->inst == n.inst && !v->released) { v->released = true; v->relStart = v->env; v->relT = 0; v->relLen = 0.008f; }
    // free voice, else steal the quietest released one, else the oldest
    Voice* best = nullptr;
    for (auto& v : voices_) if (!v->active) { best = v.get(); break; }
    if (!best) {
        for (auto& v : voices_) if (v->released && (!best || v->env < best->env)) best = v.get();
        if (!best) for (auto& v : voices_) if (!best || v->t > best->t) best = v.get();
    }
    Voice& v = *best;
    v = Voice{};
    v.in = &in; v.player = playerIdx; v.playerId = p.id; v.inst = n.inst; v.music = p.music; v.active = true;
    v.pitch = n.pitch; v.to = n.to; v.vel = n.vel;
    double spt = p.song->samplesPerTick(rate_) / rate_;
    v.gate = n.len * spt; v.glideTime = std::max(1e-3, n.len * spt);
    float pan = std::clamp(in.pan, -1.f, 1.f);
    v.panL = std::cos((pan + 1) * kPi / 4); v.panR = std::sin((pan + 1) * kPi / 4);
    v.lfsr = 0x7FFF ^ (noiseSeed_ = noiseSeed_ * 1664525u + 1013904223u) >> 17;
    if (v.lfsr == 0) v.lfsr = 1;
}

void Synth::advancePlayer(Player& p, int idx, double ticks) {
    if (!p.active || !p.song) return;
    const Song& s = *p.song;
    double end = p.pos + ticks;
    for (;;) {
        while (p.next < s.notes.size() && s.notes[p.next].tick < std::min<double>(end, s.length)) {
            startNote(p, idx, s.notes[p.next]);
            ++p.next;
        }
        if (end < s.length) break;
        if (!p.loop) { p.active = false; return; }      // finished; its voices ring out
        int loopStart = std::max(0, s.loop);
        if (s.length - loopStart <= 0) { p.active = false; return; }
        end -= (s.length - loopStart);
        p.next = 0;
        while (p.next < s.notes.size() && s.notes[p.next].tick < loopStart) ++p.next;
    }
    p.pos = end;
}

static inline float polyblep(double t, double dt) {
    if (t < dt) { t /= dt; return static_cast<float>(t + t - t * t - 1.0); }
    if (t > 1.0 - dt) { t = (t - 1.0) / dt; return static_cast<float>(t * t + t + t + 1.0); }
    return 0.f;
}

void Synth::renderVoice(Voice& v, float* l, float* r, float* dl, float* dr, float* vl, float* vr, int frames) {
    const Instrument& in = *v.in;
    const float dt = 1.f / rate_;
    const float vol = (v.music ? musicVol_ : sfxVol_) * in.gain * v.vel;
    for (int i = 0; i < frames; ++i) {
        // envelope
        float e;
        if (!v.released && v.t >= v.gate) { v.released = true; v.relStart = v.env; v.relT = 0; v.relLen = std::max(0.003f, in.r); }
        if (v.released) {
            v.relT += dt;
            e = v.relStart * std::exp(static_cast<float>(-5.0 * v.relT / v.relLen));
            if (v.relT > v.relLen * 1.6) { v.active = false; return; }
        } else if (v.t < in.a) {
            e = static_cast<float>(v.t / std::max(1e-4f, in.a));
        } else {
            float td = static_cast<float>(v.t - in.a);
            e = in.s + (1.f - in.s) * std::exp(-4.f * td / std::max(1e-3f, in.d));
        }
        v.env = e;
        // pitch
        float p = v.pitch;
        if (!std::isnan(v.to)) p += (v.to - v.pitch) * static_cast<float>(std::min(1.0, v.t / v.glideTime));
        if (in.pslide != 0.f) p += in.pslide * std::exp(static_cast<float>(-v.t / std::max(1e-4f, in.pdecay)));
        if (in.vib > 0.f && v.t > in.vibDelay) {
            float ramp = std::min(1.f, static_cast<float>((v.t - in.vibDelay) / 0.15));
            p += in.vib * ramp * std::sin(2 * kPi * in.vibRate * static_cast<float>(v.t));
        }
        float freq = 440.f * std::exp2((p - 69.f) / 12.f);
        double inc = freq / rate_;
        float x = 0.f;
        switch (in.wave) {
        case Wave::Pulse: {
            float duty = in.duty + in.pwm * std::sin(2 * kPi * in.pwmRate * static_cast<float>(v.t));
            duty = std::clamp(duty, 0.05f, 0.95f);
            auto pulse = [&](double ph, double dinc) {
                float y = ph < duty ? 1.f : -1.f;
                y += polyblep(ph, dinc);
                double ph2 = ph - duty; if (ph2 < 0) ph2 += 1;
                y -= polyblep(ph2, dinc);
                return y;
            };
            x = pulse(v.ph1, inc);
            if (in.mix2 > 0) { double i2 = inc * std::exp2(in.oct2 + in.detune / 1200.f); x += in.mix2 * pulse(v.ph2, i2); v.ph2 += i2; if (v.ph2 >= 1) v.ph2 -= 1; }
            break;
        }
        case Wave::Saw: {
            auto saw = [&](double ph, double dinc) { return static_cast<float>(2 * ph - 1) - polyblep(ph, dinc); };
            x = saw(v.ph1, inc);
            if (in.mix2 > 0) { double i2 = inc * std::exp2(in.oct2 + in.detune / 1200.f); x += in.mix2 * saw(v.ph2, i2); v.ph2 += i2; if (v.ph2 >= 1) v.ph2 -= 1; }
            break;
        }
        case Wave::Tri: {
            auto tri = [](double ph) { return static_cast<float>(ph < 0.5 ? 4 * ph - 1 : 3 - 4 * ph); };
            x = tri(v.ph1);
            if (in.mix2 > 0) { double i2 = inc * std::exp2(in.oct2 + in.detune / 1200.f); x += in.mix2 * tri(v.ph2); v.ph2 += i2; if (v.ph2 >= 1) v.ph2 -= 1; }
            break;
        }
        case Wave::Sine:
            x = std::sin(2 * kPi * static_cast<float>(v.ph1));
            if (in.mix2 > 0) { double i2 = inc * std::exp2(in.oct2 + in.detune / 1200.f); x += in.mix2 * std::sin(2 * kPi * static_cast<float>(v.ph2)); v.ph2 += i2; if (v.ph2 >= 1) v.ph2 -= 1; }
            break;
        case Wave::Noise: case Wave::Metal: {
            // shift register clocked at the note frequency (x noiserate); "metal" uses a short 7-bit loop
            v.nph += inc * in.noiseRate * 8.0;
            while (v.nph >= 1.0) {
                v.nph -= 1.0;
                uint32_t bit = in.wave == Wave::Metal ? ((v.lfsr ^ (v.lfsr >> 1)) & 1) : ((v.lfsr ^ (v.lfsr >> 1)) & 1);
                v.lfsr = (v.lfsr >> 1) | (bit << (in.wave == Wave::Metal ? 6 : 14));
                v.nval = (v.lfsr & 1) ? 1.f : -1.f;
            }
            x = v.nval;
            break;
        }
        }
        v.ph1 += inc; if (v.ph1 >= 1) v.ph1 -= 1;
        if (in.sub > 0) { x += in.sub * std::sin(2 * kPi * static_cast<float>(v.phs)); v.phs += inc * 0.5; if (v.phs >= 1) v.phs -= 1; }
        // filter (state-variable low-pass), coefficients refreshed every 16 samples
        if (--v.coefCountdown <= 0) {
            v.coefCountdown = 16;
            float fc = in.cutoff * std::exp2((v.pitch - 60.f) / 12.f * in.keytrack) + in.fenv * std::exp(static_cast<float>(-v.t / std::max(1e-3f, in.fdecay)));
            fc = std::clamp(fc, 20.f, rate_ * 0.45f);
            v.g = std::tan(kPi * fc / rate_);
            v.k = 2.f - 1.9f * std::clamp(in.res, 0.f, 1.f);
        }
        if (in.cutoff < 17999.f || in.fenv > 0.f) {
            float a1 = 1.f / (1.f + v.g * (v.g + v.k)), a2 = v.g * a1, a3 = v.g * a2;
            float v3 = x - v.ic2, v1 = a1 * v.ic1 + a2 * v3, v2 = v.ic2 + a2 * v.ic1 + a3 * v3;
            v.ic1 = 2 * v1 - v.ic1; v.ic2 = 2 * v2 - v.ic2;
            x = v2;
        }
        if (in.hp > 0.f) {
            float a = 1.f / (1.f + 2 * kPi * in.hp / rate_);
            float y = a * (v.hpY + x - v.hpX); v.hpX = x; v.hpY = y; x = y;
        }
        x *= e * vol;
        float xl = x * v.panL, xr = x * v.panR;
        l[i] += xl; r[i] += xr;
        dl[i] += xl * in.delay; dr[i] += xr * in.delay;
        vl[i] += xl * in.verb; vr[i] += xr * in.verb;
        v.t += dt;
    }
}

void Synth::render(float* out, int frames) {
    std::lock_guard<std::mutex> g(mtx_);
    if (paused_) { std::fill(out, out + frames * 2, 0.f); return; }
    constexpr int kChunk = 64;
    float L[kChunk], R[kChunk], DL[kChunk], DR[kChunk], VL[kChunk], VR[kChunk];
    const Song* ms = players_[0].song;
    float tempo = ms ? ms->tempo : 120.f;
    size_t dlen = std::min(delayL_.size() - 1, static_cast<size_t>(rate_ * 60.0 / tempo * (ms ? ms->delayBeats : 0.75f)));
    float fb = ms ? ms->delayFeedback : 0.3f;
    for (int base = 0; base < frames; base += kChunk) {
        int n = std::min(kChunk, frames - base);
        for (size_t p = 0; p < players_.size(); ++p)
            if (players_[p].active) advancePlayer(players_[p], static_cast<int>(p), n / players_[p].song->samplesPerTick(rate_));
        std::fill(L, L + n, 0.f); std::fill(R, R + n, 0.f); std::fill(DL, DL + n, 0.f); std::fill(DR, DR + n, 0.f);
        std::fill(VL, VL + n, 0.f); std::fill(VR, VR + n, 0.f);
        for (auto& v : voices_) if (v->active) renderVoice(*v, L, R, DL, DR, VL, VR, n);
        for (int i = 0; i < n; ++i) {
            // ping-pong echo
            size_t rd = (delayPos_ + delayL_.size() - dlen) % delayL_.size();
            float el = delayL_[rd], er = delayR_[rd];
            delayL_[delayPos_] = DL[i] + er * fb;
            delayR_[delayPos_] = DR[i] + el * fb;
            delayPos_ = (delayPos_ + 1) % delayL_.size();
            // small room reverb (Schroeder/Moorer: 4 combs + 2 all-passes per side)
            float in = (VL[i] + VR[i]) * 0.5f, rv[2] = {0, 0};
            for (int c = 0; c < 8; ++c) {
                Comb& cb = combs_[c];
                float y = cb.buf[cb.pos];
                cb.store = y * 0.7f + cb.store * 0.3f;
                cb.buf[cb.pos] = in + cb.store * 0.80f;
                cb.pos = (cb.pos + 1) % cb.buf.size();
                rv[c >= 4] += y;
            }
            for (int a = 0; a < 4; ++a) {
                Allpass& ap = aps_[a];
                float& s = rv[a >= 2];
                float b = ap.buf[ap.pos];
                ap.buf[ap.pos] = s + b * 0.5f;
                s = b - s;
                ap.pos = (ap.pos + 1) % ap.buf.size();
            }
            float ol = L[i] + el * 0.6f + rv[0] * 0.12f, orr = R[i] + er * 0.6f + rv[1] * 0.12f;
            out[(base + i) * 2] = std::tanh(ol);
            out[(base + i) * 2 + 1] = std::tanh(orr);
        }
    }
}

} // namespace audio
