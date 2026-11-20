#!/usr/bin/env python3
"""A 0.5 x 0.5 m open-top container with 1 m high walls in an empty world.

The scene in ``env/`` provides the floor, light and textures; the four thin,
semi-transparent walls are built here in Python, with their size driven by the
constants below. The ground plane serves as the bottom of the box.

The main loop steps the physics, spawns marbles and syncs a passive viewer each
frame.

Run it with:
    ./main.py --drop-interval 0.25 --marble-count 300
    ./main.py --warp
"""

from __future__ import annotations

import argparse
import math
import time
from dataclasses import dataclass
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
POOL_SIZE = 300
SPAWN_PERIOD = 0.25  # seconds between activations
SPAWN_HEIGHT = 1.1  # drop height (m) above the box

# The unspawned pool floats here, far from the box and off-camera.
PARK_ORIGIN = (50.0, 0.0, 0.5)
PARK_SPACING = 0.2

RNG = np.random.default_rng()


@dataclass(frozen=True)
class MarbleReference:
    body_id: int
    position_address: int
    velocity_address: int


# Per-marble references (filled by build_model) and the spawn-schedule state.
_MARBLES: list[MarbleReference] = []
_next_marble = 0
_last_spawn = -math.inf


def positive_interval(value: str) -> float:
    """Parse a finite, positive drop interval in seconds."""
    interval = float(value)
    if not math.isfinite(interval) or interval <= 0.0:
        raise argparse.ArgumentTypeError(
            "drop interval must be finite and greater than zero"
        )
    return interval


def positive_count(value: str) -> int:
    """Parse a positive number of marbles."""
    count = int(value)
    if count <= 0:
        raise argparse.ArgumentTypeError("marble count must be greater than zero")
    return count


def parse_arguments(arguments: list[str] | None = None) -> argparse.Namespace:
    """Read simulation settings from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--drop-interval",
        type=positive_interval,
        default=SPAWN_PERIOD,
        help="simulated seconds between drops (default: %(default)s)",
    )
    parser.add_argument(
        "--marble-count",
        type=positive_count,
        default=POOL_SIZE,
        help="number of marbles in the cyclic pool (default: %(default)s)",
    )
    parser.add_argument(
        "--warp",
        action="store_true",
        help="run physics with MuJoCo Warp on an NVIDIA CUDA device (default: CPU)",
    )
    return parser.parse_args(arguments)


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


def build_model(marble_count: int = POOL_SIZE) -> mujoco.MjModel:
    """Load the scene, build the container and a pool of parked marbles."""
    global _next_marble, _last_spawn

    spec = mujoco.MjSpec.from_file(str(SCENE_PATH))
    build_container(spec)

    # Pre-create the marble pool far from the box. Each is weightless and spaced
    # apart, so it floats off-camera until control() teleports it into the box and
    # switches its gravity back on. Colour is fixed per marble here.
    side = math.ceil(marble_count ** (1 / 3))
    dims = (side, side, side)
    for i in range(marble_count):
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
    _next_marble = 0
    _last_spawn = -math.inf
    for i in range(marble_count):
        name = f"marble_{i:04d}"
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"{name}_free")
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        _MARBLES.append(
            MarbleReference(
                body_id=body_id,
                position_address=model.jnt_qposadr[joint_id],
                velocity_address=model.jnt_dofadr[joint_id],
            )
        )
    return model


def control(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    sim_time: float,
    drop_interval: float = SPAWN_PERIOD,
) -> None:
    """Teleport one marble into the box when the drop interval has elapsed."""
    global _next_marble, _last_spawn

    if not _MARBLES:
        return
    if sim_time - _last_spawn < drop_interval:
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
    quaternion = RNG.normal(size=4)
    quaternion /= np.linalg.norm(quaternion)

    position_address = marble.position_address
    velocity_address = marble.velocity_address
    data.qpos[position_address : position_address + 7] = [x, y, z, *quaternion]
    # Free-joint velocity is linear x/y/z followed by angular x/y/z.
    data.qvel[velocity_address : velocity_address + 3] = [0.0, 0.0, 0.0]
    data.qvel[velocity_address + 3 : velocity_address + 6] = [0.0, 0.0, 0.0]
    model.body_gravcomp[marble.body_id] = 0.0  # let it fall again


def main() -> None:
    arguments = parse_arguments()
    model = build_model(arguments.marble_count)
    data = mujoco.MjData(model)

    print(f"MuJoCo {mujoco.__version__}: {model.ngeom} geoms, {model.njnt} joints")

    if arguments.warp:
        import mujoco_warp
        import warp

        if not warp.get_cuda_devices():
            raise RuntimeError(
                "--warp requires an NVIDIA GPU and a working CUDA driver"
            )
        warp.set_device("cuda:0")
        warp_model = mujoco_warp.put_model(model)
        # Reserve contacts for a dense pile, not just the initially separated pool.
        contact_capacity = 16 * arguments.marble_count
        warp_data = mujoco_warp.put_data(
            model, data, nconmax=contact_capacity, njmax=4 * contact_capacity
        )
        print(f"Physics: MuJoCo Warp on {warp.get_device()}")
    else:
        print("Physics: MuJoCo CPU")

    steps_per_frame = math.ceil(RENDER_DT / model.opt.timestep)
    with viewer.launch_passive(model, data) as gui:
        while gui.is_running():
            frame_start = time.perf_counter()

            control(model, data, data.time, arguments.drop_interval)

            if arguments.warp:
                # Warp keeps separate device arrays, with a leading world dimension.
                warp_data.qpos.assign(data.qpos[np.newaxis, :])
                warp_data.qvel.assign(data.qvel[np.newaxis, :])
                warp_data.time.assign(np.array([data.time]))
                warp_model.body_gravcomp.assign(model.body_gravcomp[np.newaxis, :])
                for _ in range(steps_per_frame):
                    mujoco_warp.step(warp_model, warp_data)
                if (
                    warp_data.nacon.numpy()[0] > warp_data.naconmax
                    or warp_data.nefc.numpy()[0] > warp_data.njmax
                ):
                    raise RuntimeError("Warp contact or constraint capacity exceeded")
                # The passive viewer reads host-side MuJoCo data, not device arrays.
                mujoco_warp.get_data_into(data, model, warp_data)
            else:
                for _ in range(steps_per_frame):
                    mujoco.mj_step(model, data)
            gui.sync()

            # Pace the loop to roughly real time.
            remaining = RENDER_DT - (time.perf_counter() - frame_start)
            if remaining > 0:
                time.sleep(remaining)


if __name__ == "__main__":
    main()
