#!/bin/bash

set -eu

if [ $# -eq 0 ]; then
    echo "Missing command line argument"
    echo "Usage: $(basename "$0") <command>"
    exit 1
fi

uid=$(id -u)
cache_dir="$USER_WS/persistence/$uid/cache"
ccache_dir="$USER_WS/persistence/$uid/ccache"
history_file="$USER_WS/persistence/$uid/.bash_history"

mkdir -p "$cache_dir" "$ccache_dir"

rm -rf "$HOME/.cache"
ln -s "$cache_dir" "$HOME/.cache"

rm -rf "$HOME/.ccache"
ln -s "$ccache_dir" "$HOME/.ccache"

# if bash_history is not a symlink or if it does not exist, remove it and create a new symlink
if [ ! -h "$HOME/.bash_history" ]; then
    if [ -f "$HOME/.bash_history" ]; then
        rm "$HOME/.bash_history"
    fi
    touch "$history_file"
    ln -s "$history_file" "$HOME/.bash_history"
fi

echo
echo "Python    : $(python3 --version 2>&1 | cut -d' ' -f2)"
echo "MuJoCo    : $(python3 -c 'import mujoco; print(mujoco.__version__)' 2>/dev/null || echo 'not importable')"
echo "MUJOCO_GL : ${MUJOCO_GL:-<unset>}"
echo

# Readiness marker for run.sh --daemon; it must live where the container user can write.
touch "$HOME/.fixuid_complete"

exec "$@"
