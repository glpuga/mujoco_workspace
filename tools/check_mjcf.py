"""Validate MJCF models by compiling them with MuJoCo.

Usage: python3 tools/check_mjcf.py MODEL.xml [MODEL.xml ...]
"""

from __future__ import annotations

import sys

import mujoco


def check(path: str) -> bool:
    try:
        model = mujoco.MjModel.from_xml_path(path)
    except Exception as error:  # compile errors surface as ValueError
        print(f"{path}: {error}", file=sys.stderr)
        return False

    print(
        f"{path}: OK ({model.nbody} bodies, {model.njnt} joints, {model.ngeom} geoms)"
    )
    return True


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: check_mjcf.py <model.xml> [...]", file=sys.stderr)
        return 2

    results = [check(path) for path in argv]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
