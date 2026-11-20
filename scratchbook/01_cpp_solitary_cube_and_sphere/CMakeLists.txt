cmake_minimum_required(VERSION 3.16)

project(solitary_cube_and_sphere LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Locate the repository root (the directory containing AGENTS.md) so the shared
# viewer library can be added no matter how deep this exercise lives.
set(_repo_root "${CMAKE_CURRENT_SOURCE_DIR}")
while(NOT EXISTS "${_repo_root}/AGENTS.md")
  get_filename_component(_parent "${_repo_root}" DIRECTORY)
  if(_parent STREQUAL _repo_root)
    message(
      FATAL_ERROR
      "Could not find repository root above ${CMAKE_CURRENT_SOURCE_DIR}"
    )
  endif()
  set(_repo_root "${_parent}")
endwhile()

add_subdirectory(
  "${_repo_root}/libs/mujoco_viewer"
  "${CMAKE_CURRENT_BINARY_DIR}/mujoco_viewer"
)

add_executable(solitary_cube_and_sphere main.cpp)
target_link_libraries(solitary_cube_and_sphere PRIVATE mujoco_viewer)

# Bake the MJCF path from the source directory, mirroring the Python example,
# which derives it from __file__ rather than the current working directory.
set(_model_path "${CMAKE_CURRENT_SOURCE_DIR}/env/cube_and_sphere.xml")
target_compile_definitions(
  solitary_cube_and_sphere
  PRIVATE SOLITARY_MODEL_PATH="${_model_path}"
)
