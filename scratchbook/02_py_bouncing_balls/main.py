#!/usr/bin/env python3
"""Five differently coloured 25 cm balls dropped from 1 m in an empty world.

The MJCF description lives in ``env/``. Every ball is a free body spaced 0.75 m
apart, so they all fall under gravity, bounce on the floor and settle while the
viewer runs the real-time loop.

Run it with:
    ./main.py
"""

from __future__ import annotations

from pathlib import Path

import mujoco
from mujoco import viewer

MODEL_PATH = Path(__file__).parent / "env" / "bouncing_balls.xml"


def main() -> None:
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    print(f"MuJoCo {mujoco.__version__}: {model.ngeom} geoms, {model.njnt} joints")

    viewer.launch(model, data)


if __name__ == "__main__":
    main()
