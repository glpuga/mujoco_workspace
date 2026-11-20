# Marbles in a box

A transparent, open-top container with a 0.5 x 0.5 m opening and 1 m high walls.
Marbles start parked off-camera with gravity compensated. Each drop teleports one
marble above the opening, resets its linear and angular velocity, and restores
gravity. When the pool is exhausted, marbles are reused cyclically.

Run from the repository root inside the development container:

```bash
python3 scratchbook/03_py_marbles_box/main.py
python3 scratchbook/03_py_marbles_box/main.py --drop-interval 0.5 --marble-count 100
python3 scratchbook/03_py_marbles_box/main.py --warp
```

- `--drop-interval`: positive, finite simulated seconds between drops (default: 0.25).
  Drops are checked once per viewer frame, so the actual interval is rounded up
  to a frame boundary.
- `--marble-count`: positive size of the cyclic pool (default: 300).
- `--warp`: use MuJoCo Warp on the first NVIDIA CUDA device. Without this flag,
  physics uses standard CPU MuJoCo. Requesting Warp without a CUDA device is an error.

The [Docker requirements](../../docker/files/requirements.txt) include MuJoCo Warp.
After a dependency change, rebuild the image yourself with
`./docker/run.sh --build -- bash`. Warp mode requires the host NVIDIA driver and
NVIDIA Container Toolkit; do not use `--no-gpu` when starting the container for it.
Both backends use the passive viewer and need an X11 display.

Warp holds its own model and state on the device. The script uploads the pose,
velocity and gravity-compensation arrays before each frame, steps physics there,
and downloads state for the CPU viewer. Initial kernel compilation may take time.
Transfers and kernel launches can make this single-world example slower than CPU
MuJoCo; GPU simulation is most useful for many worlds running in parallel.

## Checks

Run the focused tests inside the development container without opening a window:

```bash
python3 -m unittest discover -s scratchbook/03_py_marbles_box -p test_main.py -v
```

Set `TEST_MUJOCO_WARP=1` before that command to also exercise actual CUDA physics.
