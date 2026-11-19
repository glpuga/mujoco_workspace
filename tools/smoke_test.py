"""Validate that MuJoCo works inside the development container.

Loads an inline pendulum model, steps it and checks that the state actually
evolves. Offscreen rendering is exercised only when MUJOCO_GL is set, e.g.:

    MUJOCO_GL=egl python3 tools/smoke_test.py
"""

from __future__ import annotations

import os

import mujoco
import numpy as np

STEPS = 1000
RENDER_HEIGHT = 240
RENDER_WIDTH = 320

XML = """
<mujoco model="pendulum">
  <worldbody>
    <light pos="0 0 3"/>
    <geom name="floor" type="plane" size="3 3 0.1"/>
    <body name="pole" pos="0 0 1">
      <joint name="hinge" type="hinge" axis="0 1 0"/>
      <geom name="rod" type="capsule" fromto="0 0 0 0 0 -0.8" size="0.04"/>
    </body>
  </worldbody>
</mujoco>
"""


def main() -> None:
    print(f"MuJoCo version : {mujoco.__version__}")

    model = mujoco.MjModel.from_xml_string(XML)
    data = mujoco.MjData(model)

    # The hanging pose is an equilibrium: start displaced so gravity produces motion.
    data.qpos[0] = 1.0
    mujoco.mj_forward(model, data)
    for _ in range(STEPS):
        mujoco.mj_step(model, data)

    print(f"Bodies/joints/geoms: {model.nbody}/{model.njnt}/{model.ngeom}")
    print(f"Simulated time : {data.time:.3f} s")
    print(f"Hinge angle    : {data.qpos[0]:.3f} rad")

    assert np.isfinite(data.qpos).all(), "non-finite state"
    assert abs(data.time - STEPS * model.opt.timestep) < 1e-9, f"unexpected time {data.time}"
    assert abs(data.qpos[0] - 1.0) > 1e-3, "pendulum did not move"

    if os.environ.get("MUJOCO_GL"):
        renderer = mujoco.Renderer(model, height=RENDER_HEIGHT, width=RENDER_WIDTH)
        renderer.update_scene(data)
        pixels = renderer.render()
        assert pixels.shape == (RENDER_HEIGHT, RENDER_WIDTH, 3), pixels.shape
        assert pixels.dtype == np.uint8, pixels.dtype
        print(f"Offscreen frame: {pixels.shape} {pixels.dtype} ({os.environ['MUJOCO_GL']})")
    else:
        print("Offscreen rendering skipped (set MUJOCO_GL=egl or osmesa to test)")

    print("OK")


if __name__ == "__main__":
    main()
