from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import asyncclick as click

from contact_messenger_bot.api import oauth2, services
from contact_messenger_bot.cli.commands import constants
from contact_messenger_bot.cli.commands.common import cli

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@cli.command("message-contacts")
@click.option(
    "-c",
    "--credentials",
    type=click.Path(exists=True, dir_okay=False),
    default=constants.CREDENTIALS_FILE,
    help="The path to the credentials file",
)
@click.option(
    "-t",
    "--token",
    type=click.Path(exists=False, dir_okay=False),
    default=constants.TOKEN_FILE,
    help="The path to the token file",
)
@click.option(
    "-z",
    "--zip-code-cache",
    type=click.Path(dir_okay=False),
    default=constants.ZIP_CODE_CACHE_FILE,
    help="The path to the zip code cache",
)
async def message_contacts(credentials: Path, token: Path, zip_code_cache: Path) -> None:
    with services.ZipCode(zip_code_cache) as zipcode_svc:
        creds = oauth2.CredentialsManager(credentials, token)
        contact_svc = services.Contacts(creds, zipcode_svc)
        contact_lst = contact_svc.get_contacts()

        for contact in contact_lst:
            logger.info("%s - %s %s", contact.display_name, contact.mobile_number, contact.dates)

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
    default=constants.CREDENTIALS_FILE,
    help="The path to the credentials file",
)
@click.option(
    "-t",
    "--token",
    type=click.Path(exists=False, dir_okay=False),
    default=constants.TOKEN_FILE,
    help="The path to the token file",
)
@click.option(
    "-z",
    "--zip-code-cache",
    type=click.Path(dir_okay=False),
    default=constants.ZIP_CODE_CACHE_FILE,
    help="The path to the zip code cache",
)
async def list_contacts(credentials: Path, token: Path, zip_code_cache: Path) -> None:
    with services.ZipCode(zip_code_cache) as zipcode_svc:
        creds = oauth2.CredentialsManager(credentials, token)
        contact_svc = services.Contacts(creds, zipcode_svc)
        contact_lst = contact_svc.get_contacts()

        for contact in contact_lst:
            logger.info("%s - %s %s", contact.display_name, contact.mobile_number, contact.dates)
