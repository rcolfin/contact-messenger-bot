ARG PLATFORM="linux/amd64"

FROM --platform=${PLATFORM} python:3.13-alpine AS build

ARG PACKAGE="contact-messenger-bot-functions"

ARG APPDIR="/application"

ARG BUILD_DATE=""

# Install Poetry

ENV \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    # Poetry's configuration:
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    POETRY_HOME='/usr/local'

RUN \
    wget -qO - https://install.python-poetry.org | python3 -

RUN \
    mkdir -p "${POETRY_CACHE_DIR}" \
    && chmod gua+rwxs "${POETRY_CACHE_DIR}"

# Install Package:
WORKDIR "${APPDIR}"
COPY . ./

WORKDIR "${APPDIR}/${PACKAGE}"

RUN \
    poetry install --no-interaction --no-cache --no-root --quiet \
    && rm -rf ${POETRY_CACHE_DIR}/* \
    && poetry run pip install --no-deps --no-cache-dir --quiet . \
    && find -not -name 'pyproject.toml' -not -name 'poetry.lock' -delete \
    && find -type d -empty -delete \
    && rm -rf ~/.cache/pip \
    && rm -rf ~/.local

ENV \
    GOOGLE_FUNCTION_TARGET=get_contacts

ENV \
    BUILD_TIMESTAMP=${BUILD_DATE}

EXPOSE 8080

ENTRYPOINT ["python", "-m", "contact_messenger_bot.functions"]

CMD ["gunicorn"]
