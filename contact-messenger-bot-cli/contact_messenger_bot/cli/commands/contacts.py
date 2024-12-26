from __future__ import annotations

import datetime
import json
from contextlib import contextmanager
from typing import TYPE_CHECKING

import asyncclick as click
import structlog

from contact_messenger_bot.api import constants as api_constants
from contact_messenger_bot.api import oauth2, services
from contact_messenger_bot.cli.commands import constants
from contact_messenger_bot.cli.commands.common import cli

if TYPE_CHECKING:
    from collections.abc import Generator
    from os import PathLike

logger = structlog.get_logger(__name__)


@contextmanager
def contact_service(
    credentials: PathLike, token: PathLike, zip_code_cache: PathLike, contacts_svc_cache: PathLike
) -> Generator[services.Contacts, None, None]:
    with services.ZipCode(zip_code_cache) as zipcode_svc:
        creds = oauth2.CredentialsManager(credentials, token)
        yield services.Contacts(creds, zipcode_svc, contacts_svc_cache)


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
    "-csc",
    "--contacts-svc-cache",
    type=click.Path(dir_okay=False),
    default=constants.CONTACTS_SVC_CACHE_FILE,
    help="The path to the contacts service cache",
)
@click.option(
    "--today",
    type=str,
    default=api_constants.TODAY.strftime(constants.DATETIME_FMT),
    help="Todays's date",
)
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    help="Enable dry-run mode",
)
@click.option(
    "--load-cache/--no-load-cache",
    type=bool,
    is_flag=True,
    default=True,
    help="Flag indicating whether to use the Contact Service cache for retrieval",
)
@click.option(
    "--save-cache/--no-save-cache",
    type=bool,
    is_flag=True,
    default=True,
    help="Flag indicating whether to persist changes to the Contact Service cache",
)
@click.option("--groups", type=str, default="", help="The contact groups (comma separated).")
async def message_contacts(  # noqa: PLR0913
    credentials: PathLike,
    token: PathLike,
    zip_code_cache: PathLike,
    contacts_svc_cache: PathLike,
    today: str,
    groups: str,
    dry_run: bool,
    load_cache: bool,
    save_cache: bool,
) -> None:
    today_dt = datetime.datetime.strptime(today, constants.DATETIME_FMT).date()  # noqa: DTZ007
    group_lst = [g for g in groups.split(",") if g]
    with contact_service(credentials, token, zip_code_cache, contacts_svc_cache) as contact_svc:
        profile = contact_svc.get_profile(load_cache=load_cache, save_cache=save_cache)
        contact_lst = contact_svc.get_contacts(groups=group_lst, load_cache=load_cache, save_cache=save_cache)
        msg_svc = services.Messaging(profile, groups=group_lst)
        msg_svc.send_messages(contact_lst, today_dt, dry_run=dry_run)


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
@click.option(
    "-csc",
    "--contacts-svc-cache",
    type=click.Path(dir_okay=False),
    default=constants.CONTACTS_SVC_CACHE_FILE,
    help="The path to the contacts service cache",
)
@click.option(
    "--load-cache/--no-load-cache",
    type=bool,
    is_flag=True,
    default=True,
    help="Flag indicating whether to use the Contact Service cache for retrieval",
)
@click.option(
    "--save-cache/--no-save-cache",
    type=bool,
    is_flag=True,
    default=True,
    help="Flag indicating whether to persist changes to the Contact Service cache",
)
async def list_contacts(  # noqa: PLR0913
    credentials: PathLike,
    token: PathLike,
    zip_code_cache: PathLike,
    contacts_svc_cache: PathLike,
    load_cache: bool,
    save_cache: bool,
) -> None:
    with contact_service(credentials, token, zip_code_cache, contacts_svc_cache) as contact_svc:
        contact_lst = contact_svc.get_contacts(load_cache=load_cache, save_cache=save_cache)

        for contact in contact_lst:
            logger.info("contact", contact=json.loads(json.dumps(contact, sort_keys=True, default=str)))


@cli.command("supported-protocols")
async def supported_protocols() -> None:
    print(services.Messaging.supported_protocols())  # noqa: T201
