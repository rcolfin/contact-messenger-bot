# contact-messenger-bot

[![CI Build](https://github.com/rcolfin/contact-messenger-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/rcolfin/contact-messenger-bot/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/rcolfin/contact-messenger-bot.svg)](https://github.com/rcolfin/contact-messenger-bot/blob/main/LICENSE)

Bot to send text messages to Google Contacts for birthday's and anniversaries.

# Install Hooks

```sh
scripts/console.sh

uvx pre-commit install
```

## Development

To bootstrap a package, cd into the directory and run:

```sh
scripts/console.sh
```

## Building Docker Image

```sh
export BUILD_DATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
export GIT_COMMIT="$(git rev-parse --short HEAD)"
docker compose build --pull
```
