#!/usr/bin/env python3
"""A blue 25 cm cube next to a red 30 cm sphere in an otherwise empty world.

The MJCF description lives in ``env/``. Both geoms are static (no joints), so
this is a purely visual scene: the model compiles and the viewer runs its
real-time loop, but nothing moves.

Run it with:
    ./main.py
"""

from __future__ import annotations

from pathlib import Path

import mujoco
from mujoco import viewer

MODEL_PATH = Path(__file__).parent / "env" / "cube_and_sphere.xml"


def main() -> None:
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    print(f"MuJoCo {mujoco.__version__}: {model.ngeom} geoms, {model.njnt} joints")

    viewer.launch(model, data)


if __name__ == "__main__":
    main()
