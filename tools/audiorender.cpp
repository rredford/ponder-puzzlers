// audiorender — render a song/effect file to a 16-bit stereo WAV (and print its levels).
//   audiorender in.song out.wav [seconds]   (default: one pass through the song plus 1.5 s tail)
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <string>
#include <vector>
#include "audio/synth.hpp"

int main(int argc, char** argv) {
    if (argc < 3) { std::fprintf(stderr, "usage: %s in.song out.wav [seconds]\n", argv[0]); return 2; }
    try {
        audio::Song song = audio::loadSong(argv[1]);
        audio::Synth syn(48000);
        double secs = argc > 3 ? std::stod(argv[3]) : song.length * song.samplesPerTick(48000) / 48000.0 + 1.5;
        song.loop = argc > 3 ? song.loop : -1;               // one pass unless a duration is given
        syn.playMusic(&song);
        size_t frames = static_cast<size_t>(secs * 48000);
        std::vector<float> buf(frames * 2);
        for (size_t at = 0; at < frames; at += 4096) syn.render(buf.data() + at * 2, static_cast<int>(std::min<size_t>(4096, frames - at)));
        double peak = 0, sum = 0;
        std::vector<int16_t> pcm(buf.size());
        for (size_t i = 0; i < buf.size(); ++i) {
            peak = std::max(peak, static_cast<double>(std::fabs(buf[i]))); sum += buf[i] * buf[i];
            pcm[i] = static_cast<int16_t>(std::lround(std::max(-1.f, std::min(1.f, buf[i])) * 32767));
        }
        FILE* f = std::fopen(argv[2], "wb");
        if (!f) { std::perror(argv[2]); return 1; }
        auto u32 = [&](uint32_t v) { std::fwrite(&v, 4, 1, f); };
        auto u16 = [&](uint16_t v) { std::fwrite(&v, 2, 1, f); };
        uint32_t bytes = static_cast<uint32_t>(pcm.size() * 2);
        std::fwrite("RIFF", 1, 4, f); u32(36 + bytes); std::fwrite("WAVEfmt ", 1, 8, f);
        u32(16); u16(1); u16(2); u32(48000); u32(48000 * 4); u16(4); u16(16);
        std::fwrite("data", 1, 4, f); u32(bytes); std::fwrite(pcm.data(), 2, pcm.size(), f);
        std::fclose(f);
        std::printf("%s: %.1f s, peak %.2f, rms %.3f\n", song.name.c_str(), secs, peak, std::sqrt(sum / buf.size()));
    } catch (const std::exception& e) { std::fprintf(stderr, "error: %s\n", e.what()); return 1; }
    return 0;
}
