from __future__ import annotations

import datetime
import logging
from contextlib import contextmanager
from http import HTTPStatus
from typing import TYPE_CHECKING

import functions_framework

from contact_messenger_bot.api import oauth2, services
from contact_messenger_bot.functions import constants, credentials, gcs

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

import flask

logger = logging.getLogger(__name__)

if constants.FUSE_SECRETS_CREDENTIALS_FILE.exists():

    @contextmanager
    def zip_code_service(dest_path: Path) -> Generator[services.ZipCode, None, None]:
        with services.ZipCode(dest_path / constants.ZIP_CODE_CACHE_FILE) as zipcode_svc:
            yield zipcode_svc
else:

    @contextmanager
    def zip_code_service(dest_path: Path) -> Generator[services.ZipCode, None, None]:
        with (
            gcs.download(dest_path, gcs.get_bucket(), constants.ZIP_CODE_CACHE_FILE) as zip_code_cache,
            services.ZipCode(zip_code_cache) as zipcode_svc,
        ):
            yield zipcode_svc


@contextmanager
def contact_service(credentials: Path, token: Path) -> Generator[services.Contacts, None, None]:
    with zip_code_service(credentials.parent) as zipcode_svc:
        creds = oauth2.CredentialsManager(credentials, token)
        yield services.Contacts(creds, zipcode_svc)


@functions_framework.http
@credentials.authenticated
def get_contacts(request: flask.Request, credentials_file: Path, token_file: Path) -> flask.Response:
    """HTTP Cloud Function that lists the contacts (to the log file).
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
        credentials_file (Path): The Path to the credentials
        token_file (Path): The Path to the cached tokens.
    Returns:
        A flask.Response
    """
    with contact_service(credentials_file, token_file) as contact_svc:
        contact_lst = contact_svc.get_contacts()

        for contact in contact_lst:
            logger.info(contact)

        return flask.make_response("", HTTPStatus.NO_CONTENT)


@functions_framework.http
@credentials.authenticated
def send_messages(request: flask.Request, credentials_file: Path, token_file: Path) -> flask.Response:
    """HTTP Cloud Function that sends a message to the contacts on their special day.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
        credentials_file (Path): The Path to the credentials
        token_file (Path): The Path to the cached tokens.
    Returns:
        A flask.Response
    """
    today = request.args.get("today")
    groups = [g for g in request.args.get("groups", "").split(",") if g]
    logger.info("send_messages invoked with today=%s, groups=%s", today, groups)

    today_dt = datetime.datetime.strptime(today, constants.DATETIME_FMT).date() if today else None  # noqa: DTZ007
    with contact_service(credentials_file, token_file) as contact_svc:
        profile = contact_svc.get_profile()
        contact_lst = contact_svc.get_contacts(groups=groups)
        msg_svc = services.Messaging(profile, groups=groups)
        msg_svc.send_messages(contact_lst, today_dt)

        return flask.make_response("", HTTPStatus.NO_CONTENT)
