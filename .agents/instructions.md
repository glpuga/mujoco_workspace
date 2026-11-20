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
- CI (`.github/workflows/`) lints all files with pre-commit and builds the image, the C++ tools and
  runs both smoke tests. Keep both workflows green; they are the reference for what "working" means.

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
- Inside the container, `~/.cache`, `~/.ccache` and `~/.bash_history` are symlinked into a
  persistent volume (`~/ws/persistence`), so they survive container removal.
- Validate Python with `python3 tools/smoke_test.py` (add `MUJOCO_GL=egl` to exercise offscreen
  rendering) and C++ with:

  ```bash
  cmake -S tools -B build/tools && cmake --build build/tools && ./build/tools/smoke_test_cpp
  ```

- The container is started by the user. Do not run `./docker/run.sh`, `docker compose run` or
  `docker exec` unprompted; ask for the container when you need to execute something inside it.

## Stage conventions

Each learning stage gets its own directory `examples/NN_stage_name/` containing:

- `README.md` — what the stage demonstrates, the concepts involved, and what to look at.
- One or more standalone Python entry points (e.g. `main.py`) runnable from the repository root.
- Optional MJCF files kept next to the code; models reused across stages go in `assets/`.

MJCF files anywhere outside `docker/` are compiled by the `mjcf-compile` pre-commit hook, so a
model that MuJoCo cannot compile cannot be committed.

Stage numbering is defined in the roadmap in `README.md`. Do not renumber existing stages.

## C++ conventions

- The image provides g++, CMake, Ninja and the pinned MuJoCo C/C++ SDK under `/usr/local`
  (`mujoco/mujoco.h`, `libmujoco.so`, `simulate`, and a minimal `mujoco::mujoco` CMake package
  config installed by the image because the release archive lacks one).
- C++ stage code lives in `examples/NN_stage_name/cpp/` with a `CMakeLists.txt` that uses
  `find_package(mujoco REQUIRED)` and links `mujoco::mujoco` (C++17).
- Build out-of-tree into the gitignored `build/` directory, e.g.
  `cmake -S examples/NN_name/cpp -B build/NN_name && cmake --build build/NN_name`.
- `ccache` is available; enable it per project with
  `-DCMAKE_CXX_COMPILER_LAUNCHER=ccache` when builds get long.
- Formatting is enforced by pre-commit (`clang-format`, Chromium style, 120 columns) and
  `.clang-tidy` is provided for manual use. CMake files are linted with `cmake-lint`.

## Code style

- Python targeted at 3.11+ (the container ships 3.12); use type hints where they add clarity.
- Prefer explicit `mujoco.MjModel` / `mujoco.MjData` / `mj_step` loops over hidden wrappers; the
  point is to learn the API.
- Keep examples small and readable; comments explain *why*, not *what*.
