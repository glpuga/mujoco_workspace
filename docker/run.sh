#!/bin/bash

# Single entry point for the development container.
# Builds the image on demand and runs the container with the compose overrides
# that apply (host networking, GPU).

set -o errexit

cd "$(dirname "$(readlink -f "$0")")"

[[ -n "${WITHIN_DEV:-}" ]] && echo "Already in the development environment!" && exit 1

# Check for stop command
if [[ "$1" == "stop" ]]; then
    SERVICE_NAME="${2:-mujoco_devel}"
    CONTAINER_NAME="${USER}_${SERVICE_NAME}"
    echo "Stopping container: ${CONTAINER_NAME}"
    docker stop ${CONTAINER_NAME} 2>/dev/null && echo "Container stopped." || echo "No running container found."
    exit 0
fi

function print_help {
    echo "Usage: $(basename $0) [-b|--build] [-D|--daemon] [-s|--service SERVICE_NAME] [--no-gpu] [-h|--help] [-- COMMAND [ARGS...]]"
    echo "       $(basename $0) stop [SERVICE_NAME]"
    echo ""
    echo "Options:"
    echo "  --build                      Build the image before starting the container."
    echo "  --daemon                     Run container in detached mode (background)."
    echo "  --service                    Set the service name (default: mujoco_devel)."
    echo "  --no-gpu                     Disable GPU acceleration (CPU-only mode)."
    echo "  --help                       Display this help message."
    echo "  --                           Pass everything after this as command and arguments to docker run."
    echo ""
    echo "Commands:"
    echo "  stop [SERVICE_NAME]          Stop the running container (default service: mujoco_devel)."
    echo ""
    echo "Examples:"
    echo "  $(basename $0)                          # Run default container"
    echo "  $(basename $0) --daemon                 # Run in background"
    echo "  $(basename $0) -- bash                  # Run bash in container"
    echo "  $(basename $0) -- python3 tools/smoke_test.py"
    echo "  $(basename $0) --build -- bash          # Build image then run bash"
    echo "  $(basename $0) stop                     # Stop default container"
}

set +o errexit
VALID_ARGS=$(OPTERR=1 getopt -o bhDs: --long build,help,daemon,service:,no-gpu -- "$@")
RET_CODE=$?
set -o errexit

if [[ $RET_CODE -eq 1 ]]; then
    print_help
    exit 1;
fi
if [[ $RET_CODE -ne 0 ]]; then
    >&2 echo "Unexpected getopt error"
    exit 1;
fi

BUILD=false
DAEMON=false
SERVICE_NAME="mujoco_devel"
USE_GPU=true
DOCKER_COMMAND=()

eval set -- "$VALID_ARGS"
while [[ "$1" != "" ]]; do
    case "$1" in
    -b | --build)
        BUILD=true
        shift
        ;;
    -D | --daemon)
        DAEMON=true
        shift
        ;;
    -s | --service)
        SERVICE_NAME="$2"
        shift 2
        ;;
    --no-gpu)
        USE_GPU=false
        shift
        ;;
    -h | --help)
        print_help
        exit 0
        ;;
    --) # start of positional arguments
        shift
        DOCKER_COMMAND=("$@")
        break
        ;;
    *)
        >&2 echo "Unrecognized positional argument: $1"
        print_help
        exit 1
        ;;
    esac
done

CONTAINER_NAME="${USER}_${SERVICE_NAME}"

# Base definition plus the overrides that apply to this run.
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.host.yml"

if [[ "$USE_GPU" = true ]]; then
    COMPOSE_FILES="${COMPOSE_FILES} -f docker-compose.gpu.yml"
fi

# Make the host X cookie available to the container so the MuJoCo viewer can
# connect. An empty file is enough for X servers running without authentication.
if [[ -n "${DISPLAY:-}" ]]; then
    XAUTH_FILE=/tmp/.docker.xauth
    touch "${XAUTH_FILE}"
    if command -v xauth >/dev/null 2>&1; then
        xauth nlist "${DISPLAY}" 2>/dev/null | sed 's/^..../ffff/' \
            | xauth -f "${XAUTH_FILE}" nmerge - 2>/dev/null || true
    fi
fi

if [[ "$BUILD" = true ]]; then
 USERID=$(id -u) GROUPID=$(id -g) \
    docker compose ${COMPOSE_FILES} build ${SERVICE_NAME} \
 && echo "Built ${SERVICE_NAME} image." || \
    { echo "Failed to build ${SERVICE_NAME} image."; exit 1; }
fi

if [[ "$DAEMON" = true ]]; then
    DETACH_FLAG="--detach"
else
    DETACH_FLAG=""
fi

USERID=$(id -u) GROUPID=$(id -g) \
    docker compose ${COMPOSE_FILES} run \
    --name ${CONTAINER_NAME} \
    ${DETACH_FLAG} \
    --rm ${SERVICE_NAME} \
    "${DOCKER_COMMAND[@]}"

if [[ "$DAEMON" = true ]]; then
    echo "Container starting in daemon mode: ${CONTAINER_NAME}"
    echo "Waiting for container initialization..."

    # Wait for the marker file created by the entrypoint
    TIMEOUT=90
    SECONDS=0
    while [[ $SECONDS -lt $TIMEOUT ]]; do
        if docker exec ${CONTAINER_NAME} test -f /home/developer/.fixuid_complete 2>/dev/null; then
            echo "Container initialized successfully."
            break
        fi
        sleep 0.5
    done

    if [[ $SECONDS -ge $TIMEOUT ]]; then
        echo "Warning: Timeout waiting for container initialization."
        exit 1
    fi

    echo "Container running in background: ${CONTAINER_NAME}"
    echo "Use '$(basename $0) stop' to stop the container."
fi
