from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, TypeVar

import functions_framework

from contact_messenger_bot.api import contacts
from contact_messenger_bot.functions import credentials

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
    assert credentials_file is not None
    contact_lst = contacts.service.get_contacts(credentials_file, token_file)

    for contact in contact_lst:
        logger.info("%s - %s %s", contact.display_name, contact.mobile_number, contact.dates)

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
    assert credentials_file is not None
    contact_lst = contacts.service.get_contacts(credentials_file, token_file)

    for contact in contact_lst:
        contact.send_message()

    return flask.make_response("", HTTPStatus.NO_CONTENT)
