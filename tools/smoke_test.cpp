// Validate that the MuJoCo C/C++ SDK is installed and usable: headers, shared
// library and CMake package config all have to resolve for this to build.
//
//   cmake -S tools -B build/tools
//   cmake --build build/tools
//   ./build/tools/smoke_test_cpp

#include <cmath>
#include <cstdio>

#include <mujoco/mujoco.h>

namespace {

constexpr int kSteps = 1000;

constexpr char kModelXml[] = R"(<mujoco model="pendulum">
  <worldbody>
    <light pos="0 0 3"/>
    <geom name="floor" type="plane" size="3 3 0.1"/>
    <body name="pole" pos="0 0 1">
      <joint name="hinge" type="hinge" axis="0 1 0"/>
      <geom name="rod" type="capsule" fromto="0 0 0 0 0 -0.8" size="0.04"/>
    </body>
  </worldbody>
</mujoco>
)";

bool WriteModelFile(const char* path) {
  std::FILE* file = std::fopen(path, "w");
  if (file == nullptr) {
    return false;
  }
  const bool ok = std::fputs(kModelXml, file) >= 0;
  std::fclose(file);
  return ok;
}

}  // namespace

int main() {
  std::printf("MuJoCo version : %s\n", mj_versionString());

  constexpr char kModelPath[] = "/tmp/mujoco_smoke_test_model.xml";
  if (!WriteModelFile(kModelPath)) {
    std::fprintf(stderr, "Could not write %s\n", kModelPath);
    return 1;
  }

  char error[1000] = {};
  mjModel* model = mj_loadXML(kModelPath, nullptr, error, static_cast<int>(sizeof(error)));
  std::remove(kModelPath);
  if (model == nullptr) {
    std::fprintf(stderr, "Could not load model: %s\n", error);
    return 1;
  }

  mjData* data = mj_makeData(model);

  // The hanging pose is an equilibrium: start displaced so gravity produces motion.
  data->qpos[0] = 1.0;
  mj_forward(model, data);
  for (int i = 0; i < kSteps; ++i) {
    mj_step(model, data);
  }

  std::printf(
      "Bodies/joints/geoms: %ld/%ld/%ld\n", static_cast<long>(model->nbody), static_cast<long>(model->njnt),
      static_cast<long>(model->ngeom));
  std::printf("Simulated time : %.3f s\n", data->time);
  std::printf("Hinge angle    : %.3f rad\n", data->qpos[0]);

  const double expected_time = kSteps * model->opt.timestep;
  const bool time_ok = std::fabs(data->time - expected_time) < 1e-9;
  const bool moved = std::fabs(data->qpos[0] - 1.0) > 1e-3;
  const bool finite = std::isfinite(data->qpos[0]);

  mj_deleteData(data);
  mj_deleteModel(model);

  if (!time_ok || !moved || !finite) {
    std::fprintf(stderr, "FAILED (time_ok=%d moved=%d finite=%d)\n", time_ok, moved, finite);
    return 1;
  }

  std::printf("OK\n");
  return 0;
}
