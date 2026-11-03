cmake_minimum_required(VERSION 3.16)
project(ponderpuzzlers CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra)

# Core engine: no dependencies.
add_library(cccore STATIC
  src/core/rom.cpp src/core/level.cpp src/core/engine.cpp src/core/tws.cpp src/core/dat.cpp)
target_include_directories(cccore PUBLIC src)

# Synthesizer for the newly composed music and effects: no dependencies.
add_library(ccaudio STATIC src/audio/synth.cpp)
target_include_directories(ccaudio PUBLIC src)
find_package(Threads REQUIRED)
target_link_libraries(ccaudio PUBLIC Threads::Threads)
add_executable(audiorender tools/audiorender.cpp)
target_link_libraries(audiorender PRIVATE ccaudio)

add_executable(selftest tools/selftest.cpp)
add_executable(levelpack tools/levelpack.cpp)
target_link_libraries(levelpack PRIVATE cccore)
target_link_libraries(selftest PRIVATE cccore)

# Game front-end (needs SDL2: e.g. `sudo apt install libsdl2-dev`).
find_package(SDL2 QUIET)
if(SDL2_FOUND)
  add_executable(ponderpuzzlers src/app/main.cpp src/app/assets.cpp src/app/ui.cpp src/app/wm.cpp)
  target_link_libraries(ponderpuzzlers PRIVATE cccore ccaudio)
  if(TARGET SDL2::SDL2-static)
    target_link_libraries(ponderpuzzlers PRIVATE SDL2::SDL2-static SDL2::SDL2main)
  elseif(TARGET SDL2::SDL2)
    target_link_libraries(ponderpuzzlers PRIVATE SDL2::SDL2 SDL2::SDL2main)
  else()
    target_include_directories(ponderpuzzlers PRIVATE ${SDL2_INCLUDE_DIRS})
    target_link_libraries(ponderpuzzlers PRIVATE ${SDL2_LIBRARIES})
  endif()
  target_compile_definitions(ponderpuzzlers PRIVATE ASSET_DIR="${CMAKE_SOURCE_DIR}/assets")
else()
  message(STATUS "SDL2 not found: building engine and selftest only")
endif()

enable_testing()
set(CC_ROM "${CMAKE_SOURCE_DIR}/rom/game.lnx" CACHE FILEPATH "Cartridge image for tests")
add_test(NAME selftest COMMAND selftest ${CC_ROM})
