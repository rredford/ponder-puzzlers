#!/bin/bash
# Build helper for Ponder Puzzlers.
#   ./build.sh              build, then start the game (double-click friendly)
#   ./build.sh run [args]   the same, passing arguments to the game (e.g. --levels CCLP1.dat)
#   ./build.sh build        build only
#   ./build.sh test         build, then run the self-test (needs your cartridge image at rom/game.lnx)
#   ./build.sh clean [...]  delete the build folder first, then do the rest as above
set -e
cd "$(dirname "$0")"

fail() {
    echo "$1" >&2
    # started by double-click without a terminal: show the message in a window if possible
    if [ ! -t 1 ]; then
        if command -v zenity >/dev/null; then zenity --error --title "Ponder Puzzlers" --text "$1" 2>/dev/null || true
        elif command -v kdialog >/dev/null; then kdialog --title "Ponder Puzzlers" --error "$1" 2>/dev/null || true
        fi
    fi
    exit 1
}

if [ "$1" = "clean" ]; then
    echo "Removing build folder..."
    rm -rf build
    shift
fi

cmake -S . -B build || fail "CMake failed. Install the build tools: sudo apt install build-essential cmake libsdl2-dev"
cmake --build build -j"$(nproc 2>/dev/null || echo 2)" || fail "The build failed (see the terminal output)."

case "$1" in
build)
    echo "Done. Start the game with:  ./build/ponderpuzzlers   (or ./build.sh)"
    ;;
test)
    if [ ! -f rom/game.lnx ]; then
        echo "The self-test needs your own cartridge image at rom/game.lnx (it is not included)." >&2
        exit 1
    fi
    ctest --test-dir build --output-on-failure
    ;;
*)
    [ "$1" = "run" ] && shift
    [ -x build/ponderpuzzlers ] || fail "The game was not built (SDL2 development files missing? Install libsdl2-dev)."
    exec ./build/ponderpuzzlers "$@"
    ;;
esac
