cmake_minimum_required(VERSION 3.16)

# Build standalone (cmake -S libs/mujoco_viewer ...) or as a subproject of an
# exercise that calls add_subdirectory().
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  project(mujoco_viewer LANGUAGES CXX)
endif()

find_package(mujoco REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(GLFW REQUIRED IMPORTED_TARGET glfw3)

add_library(mujoco_viewer STATIC src/viewer.cpp)
target_compile_features(mujoco_viewer PUBLIC cxx_std_17)
target_include_directories(
  mujoco_viewer
  PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include"
)
target_link_libraries(
  mujoco_viewer
  PUBLIC mujoco::mujoco
  PRIVATE PkgConfig::GLFW
)
target_compile_options(mujoco_viewer PRIVATE -Wall -Wextra)
