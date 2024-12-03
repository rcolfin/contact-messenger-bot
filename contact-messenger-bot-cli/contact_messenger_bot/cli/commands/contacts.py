from __future__ import annotations

import logging
from pathlib import Path

import asyncclick as click

from contact_messenger_bot.api import contacts
from contact_messenger_bot.cli.commands.common import cli

logger = logging.getLogger(__name__)


@cli.command("message-contacts")
@click.option(
    "-c",
    "--credentials",
    type=click.Path(exists=True, dir_okay=False),
    default=contacts.constants.CREDENTIALS_FILE,
    help="The path to the credentials file",
)
@click.option(
    "-t",
    "--token",
    type=click.Path(exists=False, dir_okay=False),
    default=contacts.constants.TOKEN_FILE,
    help="The path to the token file",
)
async def message_contacts(credentials: Path, token: Path) -> None:
    contact_lst = contacts.service.get_contacts(Path(credentials), Path(token))

    for contact in contact_lst:
        for dt_type, date in contact.dates:
            logger.info(
                "Send text to %s, on %s with %s",
                contact.mobile_number,
                date,
                dt_type.format(contact.given_name),
            )

        logger.debug("%s - %s %s", contact.display_name, contact.mobile_number, contact.dates)


@cli.command("list-contacts")
@click.option(
    "-c",
    "--credentials",
    type=click.Path(exists=True, dir_okay=False),
    default=contacts.constants.CREDENTIALS_FILE,
    help="The path to the credentials file",
)
@click.option(
    "-t",
    "--token",
    type=click.Path(exists=False, dir_okay=False),
    default=contacts.constants.TOKEN_FILE,
    help="The path to the token file",
)
async def list_contacts(credentials: Path, token: Path) -> None:
    contact_lst = contacts.service.get_contacts(Path(credentials), Path(token))

    for contact in contact_lst:
        logger.info("%s - %s %s", contact.display_name, contact.mobile_number, contact.dates)
