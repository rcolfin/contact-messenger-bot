from __future__ import annotations

import datetime
import json
from contextlib import contextmanager
from http import HTTPStatus
from typing import TYPE_CHECKING

import functions_framework
import structlog

from contact_messenger_bot.api import oauth2, services, utils
from contact_messenger_bot.functions import constants, credentials, gcs

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

import flask

logger = structlog.get_logger(__name__)

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


if constants.FUSE_SECRETS_CONTACTS_SVC_CACHE_FILE.exists():

    @contextmanager
    def cache_svc_cache_file(dest_path: Path) -> Generator[Path, None, None]:
        yield dest_path / constants.CONTACTS_SVC_CACHE_FILE
else:

    @contextmanager
    def cache_svc_cache_file(dest_path: Path) -> Generator[Path, None, None]:
        with (
            gcs.download(dest_path, gcs.get_bucket(), constants.CONTACTS_SVC_CACHE_FILE) as contact_svc_cache_file,
        ):
            yield contact_svc_cache_file


@contextmanager
def contact_service(credentials: Path, token: Path) -> Generator[services.Contacts, None, None]:
    with (
        cache_svc_cache_file(credentials.parent) as contact_svc_cache_file,
        zip_code_service(credentials.parent) as zipcode_svc,
    ):
        creds = oauth2.CredentialsManager(credentials, token)
        yield services.Contacts(creds, zipcode_svc, contact_svc_cache_file)


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
    load_cache = utils.is_truthy(request.args.get("load-cache"), default=True)
    save_cache = utils.is_truthy(request.args.get("save-cache"), default=True)
    logger.info("get_contacts invoked", load_cache=load_cache, save_cache=save_cache)
    with contact_service(credentials_file, token_file) as contact_svc:
        contact_lst = contact_svc.get_contacts(load_cache=load_cache, save_cache=save_cache)

        for contact in contact_lst:
            logger.info("contact", contact=json.loads(json.dumps(contact, sort_keys=True, default=str)))

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
    date = request.args.get("date")
    groups = [g for g in request.args.get("groups", "").split(",") if g]
    dry_run = utils.is_truthy(request.args.get("dry-run"))
    load_cache = utils.is_truthy(request.args.get("load-cache"), default=True)
    save_cache = utils.is_truthy(request.args.get("save-cache"), default=True)
    logger.info("send_messages invoked", date=date, groups=groups, dry_run=dry_run)

    try:
        date_dt = (
            datetime.datetime.strptime(date, constants.DATE_FMT).replace(tzinfo=datetime.UTC).date() if date else None
        )
    except ValueError:
        return flask.make_response("", HTTPStatus.BAD_REQUEST)

    with contact_service(credentials_file, token_file) as contact_svc:
        profile = contact_svc.get_profile(load_cache=load_cache, save_cache=save_cache)
        contact_lst = contact_svc.get_contacts(groups=groups, load_cache=load_cache, save_cache=save_cache)
        msg_svc = services.Messaging(profile, groups=groups)
        msg_svc.send_messages(contact_lst, date_dt, dry_run=dry_run)

        return flask.make_response("", HTTPStatus.NO_CONTENT)
