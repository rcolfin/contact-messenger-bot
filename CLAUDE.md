# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**contact-messenger-bot** is a bot that sends text messages and emails to Google Contacts for birthdays and anniversaries. It's a Python monorepo with three packages:

- **contact-messenger-bot-api**: Core library providing services for Google People API integration, messaging (SMS via Twilio, email), timezone/zipcode lookups, and OAuth2 credential management
- **contact-messenger-bot-cli**: Command-line interface for interacting with the API (e.g., listing contacts, sending messages)
- **contact-messenger-bot-functions**: Google Cloud Run function wrappers that expose HTTP endpoints for the bot functionality

## Development Environment

### Setup

The project uses `uv` (via `uvx`) as the package manager. To enter a managed development environment:

```bash
scripts/console.sh
```

This script sets up Python and uv for the current shell. All development commands should be run from within this environment.

### Python Version

- Requires Python 3.14+
- Uses Pydantic for configuration and validation
- Type hints required throughout (enforced by mypy)

## Common Commands

All commands below assume you're in the managed shell (`scripts/console.sh`) and in a package directory.

### Running Tests

From a package directory:
```bash
uv run --frozen pytest
```

Run a single test file:
```bash
uv run --frozen pytest tests/test_file.py
```

Run tests matching a pattern:
```bash
uv run --frozen pytest -k "test_pattern"
```

Run tests with coverage:
```bash
uv run --frozen pytest --cov=contact_messenger_bot
```

### Code Quality (Lint, Format, Type Check)

For a single package:
```bash
scripts/check.sh
```

This runs:
1. Ruff (linting with `--fix` and formatting)
2. mypy (type checking)
3. pytest (with mypy and ruff plugins)

For all packages at once:
```bash
scripts/check-all.sh
```

### Dependency Management

Lock dependencies for a package (creates/updates `uv.lock`):
```bash
scripts/lock.sh
```

Lock all packages:
```bash
scripts/lock-all.sh
```

Install all packages (for development):
```bash
scripts/install-all.sh
```

### Running the CLI

From `contact-messenger-bot-cli`:
```bash
uv run --frozen python -m contact_messenger_bot.cli list-contacts
```

### Running Cloud Functions Locally

From `contact-messenger-bot-functions`:
```bash
uv run --frozen python -m contact_messenger_bot.functions dev
```

Or test the dev server with query parameters:
```bash
./scripts/launch.sh dev --target send_messages
# Then visit: http://127.0.0.1:8080?date=2024-11-10&groups=family&dry-run=true
```

### Docker Build

```bash
export BUILD_DATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
export GIT_COMMIT="$(git rev-parse --short HEAD)"
docker compose build --pull
```

## Architecture

### Core Services (contact-messenger-bot-api)

The API is structured around **services** — standalone classes that encapsulate interactions with external systems:

- **Contacts** (`services/contacts.py`): Wrapper around Google People API for fetching contacts, managing groups, and handling OAuth2 credentials
- **Messaging** (`services/messaging/`): Base class with implementations for SMS (Twilio) and email (SMTP); handles templating and retries
- **ZipCode** (`services/zipcode.py`): Timezone and coordinate lookups from zipcodes (used for scheduling)

### Models and Configuration

- **Models** (`models.py`): Domain objects (Contact, Message, Group, PhoneNumber, etc.) — many are enums that represent API concepts from Google
- **Settings** (`settings/`): Pydantic-based configuration for email and SMS auth, loaded from environment variables with nested delimiter support (`EMAIL__HOST`, `TEXT__ACCOUNT`, etc.)
- **Messages** (`messages/`): Template strings for birthday/anniversary messages organized by event type

### Logging

Uses `structlog` for structured logging throughout. The logging module sets up a chain of processors for cleaner output.

### Code Style

- **Ruff** enforces a strict lint/format ruleset (over 20 rules enabled, including naming, type hints, async safety, etc.)
- **mypy** enforces strict type checking with namespace packages enabled
- **Pre-commit hooks** block commits that fail mypy, ruff, or shellcheck — enforce these before pushing
- Line length: 120 characters
- Python target version: 3.9+

### Key Patterns

- **Tenacity** for retries with exponential backoff (MAX_RETRY=2 by default)
- **OAuth2 credentials** cached on disk; credential manager handles refresh/expiry
- **Constants** module defines shared values (labels, limits, timezone info)
- **Settings pattern**: Configuration is environment-driven; factory methods construct credentials/clients from settings

## Testing

Tests use `pytest` with plugins for mypy and ruff integration:

```bash
pytest --doctest-modules --mypy --ruff --ruff-format
```

Tests are co-located with source (or in a `tests/` directory) and include:
- Unit tests for services and models
- Type stubs for external libraries (google, twilio, etc.) that don't provide proper annotations
- Doctests in code examples

## Pre-commit

The project uses pre-commit hooks (installed via `uvx pre-commit install`). Key hooks:

- `mypy-linter`: Type checking
- `shellcheck-linter`: Shell script validation
- `uv-check`: Ensures pyproject.toml is valid
- `ruff`: Linting and formatting
- `nbstripout`: Strips metadata from Jupyter notebooks

Hooks run on staged files before commit; bypass only in exceptional cases.

## Secrets and Credentials

- Google OAuth tokens are stored in `token.json` (gitignored)
- Credentials can be downloaded from GCS: `gcloud storage cp gs://contact-messenger-4ed7624155de0493/* .`
- Email/SMS credentials are sourced from environment variables (not committed)
- Private keys are detected by pre-commit hooks and will block commits

## When Touching Multiple Packages

If your change affects more than one package (e.g., updating a shared type in the API), you must:
1. Update the affected package
2. Run `scripts/check-all.sh` to verify all packages still pass
3. Lock dependencies if you modified `pyproject.toml`: `scripts/lock-all.sh`
4. Commit the changes together with all affected `pyproject.toml` and `uv.lock` files
