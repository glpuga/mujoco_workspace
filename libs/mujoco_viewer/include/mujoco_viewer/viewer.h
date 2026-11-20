#ifndef MUJOCO_VIEWER_VIEWER_H_
#define MUJOCO_VIEWER_VIEWER_H_

#include <string>

#include <mujoco/mujoco.h>

namespace mujoco_viewer {

// Knobs for the interactive window. Defaults mirror MuJoCo's own samples.
struct Options {
  int width = 1200;
  int height = 900;
  std::string title = "MuJoCo";

  // Simulated seconds to advance per rendered frame. Physics is stepped until
  // this much simulated time has elapsed, so a model that is faster than
  // wall-clock appears to move in real time. Defaults to 60 fps.
  double frame_interval = 1.0 / 60.0;

  // Upper bound on the number of geoms the render scene can hold.
  int max_geoms = 2000;
};

// Open an interactive MuJoCo window for `model`/`data` and run until the user
// closes it, mirroring Python's `mujoco.viewer.launch(model, data)`.
//
// Ownership of `model` and `data` stays with the caller; the viewer only reads
// the model and steps the data. Pause / Reset / Play buttons run along the top
// of the window. Drag to orbit/pan/zoom (hold Shift to move or rotate
// horizontally). Hold Ctrl and drag a body to push it (left button rotates,
// right button translates); press Backspace to reset the simulation.
//
// Returns false if GLFW or the window could not be initialized, for example when
// no display is available.
bool Launch(mjModel* model, mjData* data, const Options& options = {});

}  // namespace mujoco_viewer

#endif  // MUJOCO_VIEWER_VIEWER_H_
