# Minimal CMake package configuration for the prebuilt MuJoCo release archive.
#
# The release tarball ships headers, shared libraries and samples, but no CMake
# package config of its own. This file is installed by docker/Dockerfile next to
# the SDK so that downstream projects can use the standard:
#
#   find_package(mujoco REQUIRED)
#   target_link_libraries(myapp PRIVATE mujoco::mujoco)

set(mujoco_VERSION "@MUJOCO_VERSION@")

if(NOT TARGET mujoco::mujoco)
  get_filename_component(
    _mujoco_prefix "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE
  )

  add_library(mujoco::mujoco SHARED IMPORTED)
  set_target_properties(
    mujoco::mujoco
    PROPERTIES IMPORTED_LOCATION "${_mujoco_prefix}/lib/libmujoco.so"
               INTERFACE_INCLUDE_DIRECTORIES "${_mujoco_prefix}/include"
  )

  find_package(Threads REQUIRED)
  set_property(
    TARGET mujoco::mujoco
    APPEND
    PROPERTY INTERFACE_LINK_LIBRARIES Threads::Threads
  )

  unset(_mujoco_prefix)
endif()

set(mujoco_FOUND TRUE)
