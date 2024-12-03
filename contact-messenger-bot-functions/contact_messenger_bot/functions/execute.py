from __future__ import annotations

import logging
import sys
from http import HTTPStatus
from typing import TYPE_CHECKING, TypeVar

import functions_framework

from contact_messenger_bot.api import contacts

from . import credentials

if TYPE_CHECKING:
    from pathlib import Path

    import flask

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

RetType = TypeVar("RetType")


@functions_framework.http
@credentials.authenticated
def execute(request: flask.Request, credentials_file: Path | None, token_file: Path | None) -> tuple[str, HTTPStatus]:
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    assert credentials_file is not None
    contact_lst = contacts.service.get_contacts(credentials_file, token_file)

    for contact in contact_lst:
        logger.info("%s - %s %s", contact.display_name, contact.mobile_number, contact.dates)

    return ("", HTTPStatus.NO_CONTENT)


if __name__ == "__main__":
    execute(None)
