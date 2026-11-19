# mujoco_workspace

A personal, incremental learning project for [MuJoCo](https://mujoco.org), built around the 4.0
release line (4.0.1 at the time of writing) that was presented at CoRL.

## Intent

This repository is a **learning workspace, not a product**. Its purpose is to build up MuJoCo
knowledge deliberately, in small steps, from the simplest possible model to progressively more
complex simulation, control and learning setups.

The guiding idea is that every stage should be:

- **Runnable** — each stage is a self-contained example with its own entry point.
- **Small** — one new concept at a time, so nothing is hand-waved.
- **Reproducible** — everything runs inside the same containerized environment, so the workspace can
  move between computers (and operating system upgrades) without being rebuilt from scratch.
- **Documented** — each stage records what was learned and why the model is built the way it is.

The container follows the same conventions already used in sibling projects (`monaco_f1tenth`,
`svdsim`), so the day-to-day workflow — `./docker/run.sh --build`, shell inside the container,
source tree bind-mounted from the host, persistent cache volume — stays familiar. Those conventions
are described in [`documentation/development_environment.md`](documentation/development_environment.md).

## Non-goals

- Not a fork of, or contribution to, MuJoCo itself.
- Not a general-purpose robotics framework; ROS 2 is only added if and when a stage actually needs it.
- No fixed timeline. Depth over speed.

## Learning roadmap

Stages are ordered from "does the simulator run at all" to "complex scene with learned control".
Each stage lives in its own directory and is expected to be revisited and refined over time.

| Stage | Focus | Key ideas |
|-------|-------|-----------|
| 0 | Dev environment | Container, viewer, headless rendering sanity check |
| 1 | MJCF basics | Bodies, joints, geoms, meshes, `mj_step` loop, model inspection |
| 2 | Actuation & control | Position/velocity/motor actuators, PD control, computed torque |
| 3 | Contact & constraints | Collision geoms, friction, solvers, stability |
| 4 | Sensors & observation | Sensors in MJCF, noisy measurements, state estimation basics |
| 5 | Rendering as data | Offscreen cameras, depth/segmentation, EGL/OSMesa heads |
| 6 | Optimization-based control | Trajectory optimization, MPC-style loops |
| 7 | Learning | RL environments, `mujoco` bindings, optionally MJX |
| 8 | Complex scenes | Multi-body scenes, assets pipeline, domain randomization |

The roadmap is intentionally coarse — exact topics will shift as understanding grows.

## Repository layout

Planned structure; directories appear as the corresponding stage begins.

```
.
├── docker/                       # Development environment (Dockerfile, compose, run.sh)
├── documentation/                # Environment and stage notes
├── examples/                     # One directory per learning stage
│   └── NN_stage_name/
├── assets/                       # Shared MJCF models and meshes
├── tools/                        # Validation and utility scripts
└── notebooks/                    # Exploratory notebooks, if useful
```

## Environment

The development environment is containerized and driven through a single entry point:

```bash
./docker/run.sh --build -- bash              # build the image, then open a shell
./docker/run.sh -- bash                      # shell into an existing image
./docker/run.sh -- python3 tools/smoke_test.py
./docker/run.sh --daemon                     # background container
./docker/run.sh stop                         # stop it
```

The source tree is bind-mounted into the container, so edits on the host are visible immediately.
GPU support is on by default (`--no-gpu` disables it). See
[`documentation/development_environment.md`](documentation/development_environment.md) for the
conventions this environment follows and the decisions taken.

Validate a freshly built image with:

```bash
./docker/run.sh -- python3 tools/smoke_test.py
MUJOCO_GL=egl ./docker/run.sh -- python3 tools/smoke_test.py   # also exercise offscreen render
```

## Status

- [x] Project intent documented
- [x] Dockerized development environment
- [ ] Stage 0: environment validation (viewer + headless render)
- [ ] Stage 1: MJCF basics

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
