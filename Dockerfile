ARG PLATFORM="linux/amd64"

FROM --platform=${PLATFORM} mambaorg/micromamba:alpine AS build

ARG PACKAGES="python=3.13 pip poetry"

ARG PACKAGE="contact-messenger-bot-functions"

ARG APPDIR="/application"

# Need to run as root:
USER "root"

# Setup micromamba and poetry

ENV \
    PATH=$PATH:/opt/conda/bin/ \
    POETRY_VIRTUALENVS_PATH=/opt/conda/envs

# Update micromamba and install poetry:
RUN \
    mkdir -p ~/.mamba/pkgs \
    && micromamba self-update -q \
    && micromamba install -qy ${PACKAGES} \
    && rm -rf /opt/conda/pkgs

ENV \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    MAMBA_SKIP_ACTIVATE=1 \
    POETRY_CACHE_DIR='/var/cache/pypoetry'

RUN \
    mkdir -p "${POETRY_CACHE_DIR}" \
    && chmod gua+rwxs "${POETRY_CACHE_DIR}"

USER "${MAMBA_USER}"

# Install Package:
WORKDIR "${APPDIR}"
COPY . ./

WORKDIR "${APPDIR}/${PACKAGE}"

RUN \
    poetry install --no-interaction --no-cache --no-root \
    && rm -rf ${POETRY_CACHE_DIR}/* \
    && poetry run pip install --no-deps --no-cache-dir . \
    && find -not -name 'pyproject.toml' -not -name 'poetry.lock' -delete \
    && find -type d -empty -delete \
    && rm -rf ~/.cache/pip \
    && rm -rf ~/.local

RUN \
    #/bin/micromamba shell init --shell bash \
    #&& echo 'source /usr/local/bin/_activate_current_env.sh' >> ~/.bashrc \
    echo "/opt/conda/bin/poetry shell -C ${APPDIR}/${PACKAGE}" >> ~/.bashrc

ENTRYPOINT ["poetry", "run"]
