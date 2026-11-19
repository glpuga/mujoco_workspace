# syntax=docker/dockerfile:1

# Development image for the MuJoCo learning workspace.
#
# Layout follows the conventions used in ../monaco_f1tenth/docker and ../svdsim/docker:
# a base stage with system tooling and a "devel" stage with the project user and Python
# environment. The source tree is bind-mounted at run time, never copied into the image.

FROM ubuntu:noble AS mujoco_service_image_base

ARG USER=developer
ARG GROUP=developer

# Scoped to the build; an ENV here would make every later apt run noninteractive.
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Argentina/Buenos_Aires

WORKDIR /root

RUN apt-get update \
 && apt-get install --no-install-recommends -y \
    adduser \
    bash-completion \
    ca-certificates \
    curl \
    gdb \
    git \
    htop \
    less \
    locate \
    mc \
    nano \
    psmisc \
    python-is-python3 \
    python3-pip \
    python3-venv \
    screen \
    sudo \
    tmux \
    tzdata \
    vim \
    wget \
    xterm \
 && rm -rf /var/lib/apt/lists/*

# OpenGL / Vulkan / X11 runtime libraries required by the MuJoCo viewer, by offscreen
# rendering (EGL, OSMesa) and by MuJoCo Studio (Filament).
RUN apt-get update \
 && apt-get install --no-install-recommends -y \
    libegl1 \
    libgl1 \
    libgl1-mesa-dri \
    libglew2.2 \
    libglfw3 \
    libglu1-mesa \
    libgles2 \
    libosmesa6 \
    libvulkan1 \
    mesa-vulkan-drivers \
    libx11-6 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxinerama1 \
    libxrandr2 \
    libxrender1 \
 && rm -rf /var/lib/apt/lists/*

# Set the timezone directly; dpkg-reconfigure would rewrite /etc/localtime from debconf.
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
 && echo "$TZ" > /etc/timezone

FROM mujoco_service_image_base AS mujoco_service_image_devel

ENV PIP_BREAK_SYSTEM_PACKAGES=1

COPY docker/files/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --requirement /tmp/requirements.txt \
 && rm /tmp/requirements.txt

RUN set -eux; \
    userdel ubuntu || true; \
    groupdel ubuntu || true; \
    addgroup --gid 1000 $GROUP; \
    adduser --uid 1000 --ingroup $GROUP --home /home/$USER --shell /bin/bash --disabled-password --gecos "" $USER; \
    adduser $USER sudo; \
    echo "$USER ALL=NOPASSWD: ALL" > /etc/sudoers.d/$USER; \
    chmod 0440 /etc/sudoers.d/$USER

USER $USER:$GROUP

ENV USER_WS=/home/$USER/ws

RUN mkdir -p $USER_WS/src

WORKDIR $USER_WS

#
# Fixuid setup

COPY --chown=root:root docker/files/fixuid_config.yml /etc/fixuid/config.yml
RUN /bin/bash -c '\
    ARCH=`uname -m` && if [ "$ARCH" == "aarch64" ]; then FIXUID_ARCH="arm64"; else FIXUID_ARCH="amd64"; fi \
 && curl -SsL https://github.com/boxboat/fixuid/releases/download/v0.6.0/fixuid-0.6.0-linux-$FIXUID_ARCH.tar.gz | sudo tar -C /usr/local/bin -xzf - \
 && sudo chmod 4755 /usr/local/bin/fixuid \
 && cd /etc/fixuid \
 && sudo sed -i "s/_USER_/$USER/" config.yml \
 && sudo sed -i "s/_GROUP_/$GROUP/" config.yml \
 && echo Done installing fixuid for $FIXUID_ARCH'

#
# Final setup of the workspace

COPY --chown=$USER:$GROUP docker/files/bash_aliases /home/$USER/.bash_aliases
RUN echo "source /home/$USER/.bash_aliases" >> /home/$USER/.bashrc

RUN mkdir -p $USER_WS/persistence && chmod 777 $USER_WS/persistence

ENV WITHIN_DEV=1

# --chmod keeps the scripts executable regardless of the host checkout's file modes.
COPY --chown=root:root --chmod=0755 docker/files/fixuid_wrapper.sh /fixuid_wrapper.sh
COPY --chown=root:root --chmod=0755 docker/files/entrypoint.sh /mujoco_entrypoint.sh

CMD        ["/bin/bash"]
ENTRYPOINT ["/fixuid_wrapper.sh", "fixuid", "-q", "/mujoco_entrypoint.sh"]
