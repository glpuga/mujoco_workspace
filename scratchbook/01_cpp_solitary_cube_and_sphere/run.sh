#!/usr/bin/env bash
#
# Build and run the C++ "solitary cube and sphere" example.
#
# Intended to be run inside the development container, where the MuJoCo C++ SDK
# and GLFW are available:
#   ./docker/run.sh -- bash
#   scratchbook/01_cpp_solitary_cube_and_sphere/run.sh
#
# The build tree is kept out of the source dir, under the gitignored build/.

set -euo pipefail

usage() {
  cat <<'EOF'
Build and run the C++ "solitary cube and sphere" example.

Run inside the development container, for example:
  ./docker/run.sh -- bash
  scratchbook/01_cpp_solitary_cube_and_sphere/run.sh

Options:
  --build-only   configure and compile, but do not open the viewer
  -h, --help     show this help
EOF
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"
build_dir="${repo_root}/build/01_cpp_solitary_cube_and_sphere"
binary="${build_dir}/solitary_cube_and_sphere"

build_only=0
for arg in "$@"; do
  case "${arg}" in
    --build-only)
      build_only=1
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "run.sh: unknown argument '${arg}' (try --help)" >&2
      exit 2
      ;;
  esac
done

cmake -S "${script_dir}" -B "${build_dir}"
cmake --build "${build_dir}"

if [[ "${build_only}" -eq 1 ]]; then
  echo "Built ${binary}"
  exit 0
fi

exec "${binary}"
