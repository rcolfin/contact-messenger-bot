from __future__ import annotations

import datetime
import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING

import asyncclick as click

from contact_messenger_bot.api import constants as api_constants
from contact_messenger_bot.api import oauth2, services
from contact_messenger_bot.cli.commands import constants
from contact_messenger_bot.cli.commands.common import cli

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

logger = logging.getLogger(__name__)


@contextmanager
def contact_service(credentials: Path, token: Path, zip_code_cache: Path) -> Generator[services.Contacts, None, None]:
    with services.ZipCode(zip_code_cache) as zipcode_svc:
        creds = oauth2.CredentialsManager(credentials, token)
        yield services.Contacts(creds, zipcode_svc)


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
@click.option(
    "--today",
    type=str,
    default=api_constants.TODAY.strftime(constants.DATETIME_FMT),
    help="Todays's date",
)
@click.option("--groups", type=str, help="The contact groups (comma separated).")
async def message_contacts(credentials: Path, token: Path, zip_code_cache: Path, today: str, groups: str) -> None:
    today_dt = datetime.datetime.strptime(today, constants.DATETIME_FMT).date()  # noqa: DTZ007
    with contact_service(credentials, token, zip_code_cache) as contact_svc:
        profile = contact_svc.get_profile()
        contact_lst = contact_svc.get_contacts()
        msg_svc = services.Messaging(profile, today_dt, groups=groups.split(","))
        msg_svc.send_messages(contact_lst)


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
    with contact_service(credentials, token, zip_code_cache) as contact_svc:
        contact_lst = contact_svc.get_contacts()

        for contact in contact_lst:
            logger.info("%s - %s %s", contact.display_name, contact.mobile_numbers, contact.dates)
