// A blue 25 cm cube next to a red 30 cm sphere in an otherwise empty world.
//
// C++ counterpart of scratchbook/00_py_solitary_cube_and_sphere: it loads the
// same MJCF and hands it to the shared interactive viewer. Both objects are free
// bodies, so they settle onto the floor under gravity while the window runs.
//
// Build and run from the repository root, inside the container:
//   ./docker/run.sh -- bash
//   scratchbook/01_cpp_solitary_cube_and_sphere/run.sh
//
// Or by hand:
//   cmake -S scratchbook/01_cpp_solitary_cube_and_sphere \
//         -B build/01_cpp_solitary_cube_and_sphere
//   cmake --build build/01_cpp_solitary_cube_and_sphere
//   ./build/01_cpp_solitary_cube_and_sphere/solitary_cube_and_sphere

#include <cstdio>
#include <cstdlib>

#include <mujoco/mujoco.h>
#include <mujoco_viewer/viewer.h>

// CMake injects the absolute path; this fallback keeps the file compilable on
// its own from the exercise directory.
#ifndef SOLITARY_MODEL_PATH
#define SOLITARY_MODEL_PATH "env/cube_and_sphere.xml"
#endif

int main() {
  char error[1000] = {};
  mjModel* model = mj_loadXML(SOLITARY_MODEL_PATH, nullptr, error, static_cast<int>(sizeof(error)));
  if (model == nullptr) {
    std::fprintf(stderr, "Could not load %s: %s\n", SOLITARY_MODEL_PATH, error);
    return EXIT_FAILURE;
  }

  mjData* data = mj_makeData(model);
  std::printf("MuJoCo %s: %d geoms, %d joints\n", mj_versionString(), model->ngeom, model->njnt);

  mujoco_viewer::Options options;
  options.title = "MuJoCo: cube and sphere";
  const bool launched = mujoco_viewer::Launch(model, data, options);

  mj_deleteData(data);
  mj_deleteModel(model);
  return launched ? EXIT_SUCCESS : EXIT_FAILURE;
}
