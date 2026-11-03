// The game window's X11 id, for attaching external dialogs to it (main.cpp). Kept in its own file because
// SDL_syswm.h pulls in the X11 headers, whose macros clash with names used elsewhere.
#include <SDL.h>
#include <SDL_syswm.h>
unsigned long windowX11Id(SDL_Window* w) {
#if defined(SDL_VIDEO_DRIVER_X11)
    SDL_SysWMinfo wm; SDL_VERSION(&wm.version);
    if (SDL_GetWindowWMInfo(w, &wm) && wm.subsystem == SDL_SYSWM_X11) return static_cast<unsigned long>(wm.info.x11.window);
#else
    (void)w;
#endif
    return 0;
}
