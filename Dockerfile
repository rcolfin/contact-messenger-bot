ARG PLATFORM="linux/amd64"

FROM --platform=${PLATFORM} ghcr.io/astral-sh/uv:python3.13-alpine AS build

ARG GIT_COMMIT="unknown"
ARG BUILD_DATE=""
ARG AUTHORS="rcolfin"
ARG PACKAGE="contact-messenger-bot-functions"
ARG APPDIR="/application"
ARG BUILD_DATE=""

LABEL \
    org.opencontainers.image.revision=$GIT_COMMIT \
    org.opencontainers.image.created=$BUILD_DATE \
    org.opencontainers.image.authors=$AUTHORS \
    org.opencontainers.image.description="Contact Messenger Bot Functions"

# Setup uv

ENV \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    UV_NO_CACHE=1 \
    UV_PROJECT_ENVIRONMENT="/usr/local"

# Install Package:
WORKDIR "${APPDIR}"
COPY . ./

WORKDIR "${APPDIR}/${PACKAGE}"

RUN \
    uv sync --no-dev --locked --quiet \
    && uv run --no-sync pip install --no-deps --no-cache-dir --quiet . \
    && rm -rf ./*

ENV \
    GOOGLE_FUNCTION_TARGET=get_contacts

ENV \
    GIT_COMMIT=${GIT_COMMIT} \
    BUILD_TIMESTAMP=${BUILD_DATE}


EXPOSE 8080

ENTRYPOINT ["python", "-m", "contact_messenger_bot.functions"]

CMD ["gunicorn"]
