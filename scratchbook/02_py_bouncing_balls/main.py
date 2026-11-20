#!/usr/bin/env python3
"""Five differently coloured 25 cm balls dropped from 1 m in an empty world.

The scene in ``env/`` defines only the floor, light and textures; the balls are
added programmatically with MjSpec, so their colours and contact damping live in
code instead of MJCF. Every ball is a free body, so they fall, bounce and settle
while the viewer runs the real-time loop.

Run it with:
    ./main.py
"""

from __future__ import annotations

import math
from pathlib import Path

import mujoco
import numpy as np
from mujoco import viewer

SCENE_PATH = Path(__file__).parent / "env" / "scene.xml"

RADIUS = 0.125  # 25 cm diameter
DROP_HEIGHT = 1.0
TIME_CONST = 0.02  # contact solref time constant

# name, x position, colour, and target coefficient of restitution.
# Restitution is graded linearly from 0.75 (bounciest) down to 0 (dead).
BALLS = [
    ("ball_red", -1.5, (1.0, 0.0, 0.0, 1.0), 0.75),
    ("ball_green", -0.75, (0.0, 1.0, 0.0, 1.0), 0.5625),
    ("ball_blue", 0.0, (0.0, 0.0, 1.0, 1.0), 0.375),
    ("ball_yellow", 0.75, (1.0, 1.0, 0.0, 1.0), 0.1875),
    ("ball_magenta", 1.5, (1.0, 0.0, 1.0, 1.0), 0.0),
]


def damping_ratio(restitution: float) -> float:
    """Convert a coefficient of restitution to a solref damping ratio."""
    if restitution <= 0.0:
        return 1.0  # critically damped: no rebound
    log_e = -math.log(restitution)
    return log_e / math.sqrt(math.pi**2 + log_e**2)


def build_model() -> mujoco.MjModel:
    spec = mujoco.MjSpec.from_file(str(SCENE_PATH))

    for name, x, rgba, restitution in BALLS:
        body = spec.worldbody.add_body()
        body.name = name
        body.pos = np.array([x, 0.0, DROP_HEIGHT])
        body.add_freejoint().name = f"{name}_free"

        geom = body.add_geom()
        geom.name = f"{name}_geom"
        geom.type = mujoco.mjtGeom.mjGEOM_SPHERE
        geom.size = np.array([RADIUS, 0.0, 0.0])
        geom.rgba = np.array(rgba)
        geom.solref = np.array([TIME_CONST, damping_ratio(restitution)])
        geom.priority = 1

    return spec.compile()


def main() -> None:
    model = build_model()
    data = mujoco.MjData(model)

    print(f"MuJoCo {mujoco.__version__}: {model.ngeom} geoms, {model.njnt} joints")

    viewer.launch(model, data)


if __name__ == "__main__":
    main()
