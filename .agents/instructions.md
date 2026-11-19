# mujoco_workspace — AI Assistant Instructions

## What this repository is

A personal learning workspace for MuJoCo (4.0.x), built up incrementally from simple models to
complex simulation and control. It is **not** a product and **not** a fork of MuJoCo. Depth over
speed; each stage must remain runnable and self-contained.

Read `README.md` for the roadmap and `documentation/development_environment.md` for how the
environment is put together.

## Working agreements

- **Do not commit.** Commits are made only when explicitly requested. The project uses
  [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`,
  `refactor:`, `build:`, `test:`).
- **Do not build automatically.** Only run `docker compose build` / `./docker/run.sh --build` when
  asked; building is slow and the user controls it.
- **Ask before adding dependencies.** The image is intentionally small; each new package is a
  deliberate decision recorded in `docker/files/requirements.txt`.
- Keep documentation in sync with reality. If behaviour changes, update the relevant doc in the same
  change.

## Repository layout

```
docker/            # Development environment (Dockerfile, compose, run.sh, files/)
documentation/     # Environment notes and stage documentation
examples/          # One directory per learning stage (created as stages begin)
assets/            # Shared MJCF models and meshes
tools/             # Small utility/validation scripts
```

## Environment workflow

The source tree is bind-mounted at `/home/developer/ws/src/project`; the image holds only
dependencies. Everything is driven through `docker/run.sh`:

```bash
./docker/run.sh --build -- bash              # build image, then open a shell
./docker/run.sh -- bash                      # shell into an existing image
./docker/run.sh                              # same, but exits with the shell
./docker/run.sh -- python3 tools/smoke_test.py
./docker/run.sh --daemon                     # background container
./docker/run.sh stop                         # stop it
```

Notes:

- GPU support is enabled by default; pass `--no-gpu` on machines without NVIDIA tooling.
- GUI windows need X11 access on the host (`DISPLAY`, `/tmp` is mounted). Headless rendering uses
  `MUJOCO_GL=egl` or `osmesa`.
- Inside the container, `~/.cache` and `~/.bash_history` are symlinked into a persistent volume
  (`~/ws/persistence`), so they survive container removal.
- Validate the environment with `python3 tools/smoke_test.py` (add `MUJOCO_GL=egl` to exercise
  offscreen rendering).

## Stage conventions

Each learning stage gets its own directory `examples/NN_stage_name/` containing:

- `README.md` — what the stage demonstrates, the concepts involved, and what to look at.
- One or more standalone Python entry points (e.g. `main.py`) runnable from the repository root.
- Optional MJCF files kept next to the code; models reused across stages go in `assets/`.

Stage numbering is defined in the roadmap in `README.md`. Do not renumber existing stages.

## Code style

- Python targeted at 3.11+ (the container ships 3.12); use type hints where they add clarity.
- Prefer explicit `mujoco.MjModel` / `mujoco.MjData` / `mj_step` loops over hidden wrappers; the
  point is to learn the API.
- Keep examples small and readable; comments explain *why*, not *what*.
