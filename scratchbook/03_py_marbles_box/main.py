#!/usr/bin/env python3
"""A 0.5 x 0.5 m open-top container with 1 m high walls in an empty world.

The scene in ``env/`` provides the floor, light and textures; the four thin,
semi-transparent walls are built here in Python, with their size driven by the
constants below. The ground plane serves as the bottom of the box.

The main loop steps the physics, spawns marbles and syncs a passive viewer each
frame.

Run it with:
    ./main.py
"""

from __future__ import annotations

import math
import time
from pathlib import Path

import mujoco
import numpy as np
from mujoco import viewer

SCENE_PATH = Path(__file__).parent / "env" / "scene.xml"

# Target frame interval, used both as simulated time advanced per frame and as
# the wall-clock pacing target.
RENDER_DT = 1.0 / 60.0

# Container geometry, in metres.
BOX_SIDE = 0.5  # inner width and depth
WALL_HEIGHT = 1.0
WALL_THICKNESS = 0.02
GLASS_RGBA = (0.35, 0.6, 0.95, 0.25)  # transparent walls

# Marbles.
MARBLE_RADIUS = 0.05  # 10 cm diameter
MARBLE_SOLREF = (0.02, 0.2)  # time constant, damping ratio: bouncy
POOL_SIZE = 30
SPAWN_PERIOD = 0.5  # seconds between activations
SPAWN_HEIGHT = 1.1  # drop height (m) above the box

# The unspawned pool floats here, far from the box and off-camera.
PARK_ORIGIN = (50.0, 0.0, 0.5)
PARK_SPACING = 0.2

RNG = np.random.default_rng()

# Per-marble ids/addresses (filled by build_model) and the spawn-schedule state.
_MARBLES: list[dict] = []
_next_marble = 0
_last_spawn = -SPAWN_PERIOD


def build_container(spec: mujoco.MjSpec) -> None:
    """Add the four transparent walls to the spec as one body."""
    half = BOX_SIDE / 2.0
    half_t = WALL_THICKNESS / 2.0
    outer = half + WALL_THICKNESS
    offset = half + half_t
    half_h = WALL_HEIGHT / 2.0

    body = spec.worldbody.add_body()
    body.name = "container"

    # Two walls span the full outer width; the other two fit between them.
    walls = [
        ("wall_px", (offset, 0.0, half_h), (half_t, outer, half_h)),
        ("wall_nx", (-offset, 0.0, half_h), (half_t, outer, half_h)),
        ("wall_py", (0.0, offset, half_h), (half, half_t, half_h)),
        ("wall_ny", (0.0, -offset, half_h), (half, half_t, half_h)),
    ]
    for name, pos, size in walls:
        geom = body.add_geom()
        geom.name = name
        geom.type = mujoco.mjtGeom.mjGEOM_BOX
        geom.pos = np.array(pos)
        geom.size = np.array(size)
        geom.rgba = np.array(GLASS_RGBA)


def _park_position(i: int, dims: tuple[int, int, int]) -> tuple[float, float, float]:
    """Return the grid position for marble i within a dims-sized block."""
    _, sy, sz = dims
    ix, rem = divmod(i, sy * sz)
    iy, iz = divmod(rem, sz)
    return (
        PARK_ORIGIN[0] + ix * PARK_SPACING,
        PARK_ORIGIN[1] + iy * PARK_SPACING,
        PARK_ORIGIN[2] + iz * PARK_SPACING,
    )


def build_model() -> mujoco.MjModel:
    """Load the scene, build the container and a pool of parked marbles."""
    spec = mujoco.MjSpec.from_file(str(SCENE_PATH))
    build_container(spec)

    # Pre-create the marble pool far from the box. Each is weightless and spaced
    # apart, so it floats off-camera until control() teleports it into the box and
    # switches its gravity back on. Colour is fixed per marble here.
    side = math.ceil(POOL_SIZE ** (1 / 3))
    dims = (side, side, side)
    for i in range(POOL_SIZE):
        body = spec.worldbody.add_body()
        body.name = f"marble_{i:04d}"
        body.pos = np.array(_park_position(i, dims))
        body.gravcomp = 1.0  # weightless while parked
        body.add_freejoint().name = f"marble_{i:04d}_free"

        geom = body.add_geom()
        geom.name = f"marble_{i:04d}_geom"
        geom.type = mujoco.mjtGeom.mjGEOM_SPHERE
        geom.size = np.array([MARBLE_RADIUS, 0.0, 0.0])
        geom.rgba = np.array([*RNG.random(3), 1.0])
        geom.solref = np.array(MARBLE_SOLREF)
        geom.priority = 1

    model = spec.compile()

    # The parked marbles would inflate the model's bounding box (and thus the
    # default camera framing); pin the statistics to the container instead.
    model.stat.center[:] = [0.0, 0.0, WALL_HEIGHT / 2.0]
    model.stat.extent = math.hypot(BOX_SIDE, WALL_HEIGHT)

    # Cache what control() needs to teleport a marble.
    _MARBLES.clear()
    for i in range(POOL_SIZE):
        name = f"marble_{i:04d}"
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"{name}_free")
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        _MARBLES.append(
            {
                "body": bid,
                "qposadr": model.jnt_qposadr[jid],
                "dofadr": model.jnt_dofadr[jid],
            }
        )
    return model


def control(model: mujoco.MjModel, data: mujoco.MjData, sim_time: float) -> None:
    """Teleport one parked marble into the box every SPAWN_PERIOD seconds."""
    global _next_marble, _last_spawn

    if not _MARBLES:
        return
    if sim_time - _last_spawn < SPAWN_PERIOD:
        return
    _last_spawn = sim_time

    # Reuse marbles cyclically: once the pool is exhausted, wrap to the first.
    marble = _MARBLES[_next_marble]
    _next_marble = (_next_marble + 1) % len(_MARBLES)

    # Random pose above the box opening, random orientation, at rest.
    half = BOX_SIDE / 2.0 - MARBLE_RADIUS
    x = RNG.uniform(-half, half)
    y = RNG.uniform(-half, half)
    z = SPAWN_HEIGHT + RNG.uniform(0.0, 0.5)
    quat = RNG.normal(size=4)
    quat /= np.linalg.norm(quat)

    adr = marble["qposadr"]
    data.qpos[adr : adr + 7] = [x, y, z, *quat]
    data.qvel[marble["dofadr"] : marble["dofadr"] + 6] = 0.0
    model.body_gravcomp[marble["body"]] = 0.0  # let it fall again


def main() -> None:
    model = build_model()
    data = mujoco.MjData(model)

    print(f"MuJoCo {mujoco.__version__}: {model.ngeom} geoms, {model.njnt} joints")

    with viewer.launch_passive(model, data) as gui:
        while gui.is_running():
            frame_start = time.perf_counter()

            control(model, data, data.time)

            # Advance one frame of simulated time, then push it to the viewer.
            sim_start = data.time
            while data.time - sim_start < RENDER_DT:
                mujoco.mj_step(model, data)
            gui.sync()

            # Pace the loop to roughly real time.
            remaining = RENDER_DT - (time.perf_counter() - frame_start)
            if remaining > 0:
                time.sleep(remaining)


if __name__ == "__main__":
    main()
