cmake_minimum_required(VERSION 3.16)

project(mujoco_workspace_tools LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(mujoco REQUIRED)

add_executable(smoke_test_cpp smoke_test.cpp)
target_link_libraries(smoke_test_cpp PRIVATE mujoco::mujoco)
