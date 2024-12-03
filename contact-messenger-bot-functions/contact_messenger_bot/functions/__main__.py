from __future__ import annotations

import logging
import os
import shutil
import subprocess
from multiprocessing import cpu_count
from pathlib import Path
from typing import Final

import click
import functions_framework

from contact_messenger_bot.functions import __version__, constants, function

logger = logging.getLogger(__name__)

GUNICORN_PATH: Final[str | None] = shutil.which("gunicorn")
DEFAULT_PORT: Final[int] = int(os.getenv("PORT", constants.DEFAULT_PORT))
DEFAULT_SOURCE: Final[str] = (
    os.getenv("GOOGLE_FUNCTION_SOURCE") or os.getenv("FUNCTION_SOURCE") or str(Path(function.__file__).resolve())
)
DEFAULT_TARGET: Final[str] = (
    os.getenv("GOOGLE_FUNCTION_TARGET") or os.getenv("FUNCTION_TARGET") or function.get_contacts.__name__
)


@click.group()
def cli() -> None:
    pass


@cli.command("dev")
@click.option("-s", "--source", type=str, default=DEFAULT_SOURCE, help="The function source")
@click.option("-t", "--target", type=str, default=DEFAULT_TARGET, help="The function target")
@click.option("-p", "--port", type=int, default=DEFAULT_PORT, help="Default running port.")
def dev(source: str, target: str, port: int) -> None:
    logger.info("Running v%s", __version__)
    logger.info("Configuring app with source=%s, target=%s", source, target)
    app = functions_framework.create_app(source=source, target=target)

    if constants.FUSE_SECRETS_VOLUME.exists():
        logger.info("Fuse Volume Exists: %s", list(constants.FUSE_SECRETS_VOLUME.glob("**/")))
    else:
        logger.info("Fuse Volume does not exists.")

    app.run(debug=True, host=constants.ALL_INTERFACES, port=port)


@cli.command("gunicorn")
@click.option("-s", "--source", type=str, default=DEFAULT_SOURCE, help="The function source")
@click.option("-t", "--target", type=str, default=DEFAULT_TARGET, help="The function target")
@click.option("-p", "--port", type=int, default=DEFAULT_PORT, help="Default running port.")
def gunicorn(source: str, target: str, port: int) -> None:
    build_timestamp = os.getenv("BUILD_TIMESTAMP", "").strip()
    if build_timestamp:
        build_timestamp = f" (built {build_timestamp})"

    logger.info("Running v%s%s", __version__, build_timestamp)
    logger.info("Configuring app with source=%s, target=%s", source, target)
    os.environ["FUNCTION_SOURCE"] = source
    os.environ["FUNCTION_TARGET"] = target

    if constants.FUSE_SECRETS_VOLUME.exists():
        logger.info("Fuse Volume Exists: %s", list(constants.FUSE_SECRETS_VOLUME.glob("**/")))
    else:
        logger.info("Fuse Volume does not exists.")

    if GUNICORN_PATH is None:
        message = "gunicorn not found"
        raise ValueError(message)

    args = [
        GUNICORN_PATH,
        "--bind",
        f"{constants.ALL_INTERFACES}:{port}",
        "--workers",
        "1",
        "--threads",
        str(cpu_count()),
        "--timeout",
        "0",
        "--log-level=info",
        "contact_messenger_bot.functions.app:create_app()",
    ]
    subprocess.check_output(args)  # noqa: S603


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-4s\t%(message)s",
    )

    cli()


if __name__ == "__main__":
    main()
