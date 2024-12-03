from __future__ import annotations

import logging

from contact_messenger_bot.cli.commands import cli

logger = logging.getLogger(__name__)


def main() -> None:
    cli(_anyio_backend="asyncio")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-4s\t%(message)s",
    )

    main()
