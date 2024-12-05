from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, TypeVar

import functions_framework

from contact_messenger_bot.api import oauth2, services
from contact_messenger_bot.functions import constants, credentials, gcs

if TYPE_CHECKING:
    from pathlib import Path

import flask

logger = logging.getLogger(__name__)

RetType = TypeVar("RetType")


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
    with (
        gcs.download(credentials_file.parent, gcs.get_bucket(), constants.ZIP_CODE_CACHE_FILE) as zip_code_cache,
        services.ZipCode(zip_code_cache) as zipcode_svc,
    ):
        creds = oauth2.CredentialsManager(credentials_file, token_file)
        contact_svc = services.Contacts(creds, zipcode_svc)
        contact_lst = contact_svc.get_contacts()

        for contact in contact_lst:
            contact.send_message()

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
    with (
        gcs.download(credentials_file.parent, gcs.get_bucket(), constants.ZIP_CODE_CACHE_FILE) as zip_code_cache,
        services.ZipCode(zip_code_cache) as zipcode_svc,
    ):
        creds = oauth2.CredentialsManager(credentials_file, token_file)
        contact_svc = services.Contacts(creds, zipcode_svc)
        contact_lst = contact_svc.get_contacts()

        for contact in contact_lst:
            contact.send_message()

        return flask.make_response("", HTTPStatus.NO_CONTENT)
