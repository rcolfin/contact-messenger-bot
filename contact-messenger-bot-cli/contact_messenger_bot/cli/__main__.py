from __future__ import annotations

from contact_messenger_bot.api import logging
from contact_messenger_bot.cli.commands import cli


def main() -> None:
    cli(_anyio_backend="asyncio")


if __name__ == "__main__":
    logging.configure()

    main()
