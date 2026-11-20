# mujoco_viewer

A small, reusable C++ wrapper around MuJoCo's visualisation API (`mjvScene`, `mjrContext`) and
GLFW. It gives C++ exercises the same one-call viewer that Python gets from
`mujoco.viewer.launch(model, data)`, so the render loop does not have to be copied into every
project.

## Usage

```cpp
#include <mujoco/mujoco.h>
#include <mujoco_viewer/viewer.h>

char error[1000] = {};
mjModel* model = mj_loadXML("model.xml", nullptr, error, sizeof(error));
mjData* data = mj_makeData(model);

mujoco_viewer::Options options;
options.title = "My model";
mujoco_viewer::Launch(model, data, options);  // blocks until the window is closed

mj_deleteData(data);
mj_deleteModel(model);
```

The caller keeps ownership of `model` and `data`; the viewer only reads the model and steps the
data. Pause / Reset / Play buttons are drawn along the top of the window. Drag to orbit/pan/zoom and
hold Shift to move or rotate horizontally. Hold Ctrl and drag a body to push it (left button rotates,
right button translates) — the same perturbation the Python `mujoco.viewer` offers. Press Backspace
to reset the simulation.

## Consuming it from an exercise

There is no install step; add it as a subproject and link the target:

```cmake
add_subdirectory(
  "${_repo_root}/libs/mujoco_viewer"
  "${CMAKE_CURRENT_BINARY_DIR}/mujoco_viewer"
)
target_link_libraries(my_exercise PRIVATE mujoco_viewer)
```

`find_package(mujoco)` and the GLFW pkg-config module are resolved inside this directory's
`CMakeLists.txt`, so an exercise only needs to link `mujoco_viewer`.

## Building standalone

```bash
cmake -S libs/mujoco_viewer -B build/mujoco_viewer
cmake --build build/mujoco_viewer
```
