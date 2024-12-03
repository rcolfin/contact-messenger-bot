from __future__ import annotations

import contextlib
import datetime
import logging
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Final

import backoff
import google.auth.exceptions
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from . import constants, models, utils

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


logger = logging.getLogger(__name__)


def _wrap_creds(creds: Credentials, token_file: Path, save: bool = False) -> Credentials:
    refresh_orig: Final[Callable[[Request], None]] = creds.refresh

    def save_token() -> None:
        logger.info("Saving token to %s", token_file)
        token_file.write_text(creds.to_json())

    @wraps(creds.refresh)
    def refresh(request: Request) -> None:
        refresh_orig(request)
        save_token()

    creds.refresh = refresh

    if save:
        save_token()

    return creds


@backoff.on_exception(backoff.expo, AttributeError, max_tries=constants.MAX_RETRY)
def _create_service(credentials_file: Path, token_file: Path) -> Resource:
    creds = None
    if token_file.exists():
        with contextlib.suppress(ValueError):
            logger.debug("Authenticating %s", token_file)
            creds = _wrap_creds(Credentials.from_authorized_user_file(str(token_file), constants.SCOPES), token_file)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.debug("Refreshing credentials")
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), constants.SCOPES)
            creds = _wrap_creds(flow.run_local_server(port=0), token_file, save=True)

    return build("people", "v1", credentials=creds, cache_discovery=False)


def _get_contacts(service: Resource, fields: str) -> Iterable[dict[str, Any]]:
    # Call the People API
    next_page_token = None
    start_idx = 0
    page_count = 1
    while True:
        request = (
            service.people()
            .connections()
            .list(
                resourceName="people/me",
                pageSize=constants.MAX_PAGE_SIZE,
                pageToken=next_page_token,
                personFields=fields,
            )
        )

        results = request.execute()
        connections = results.get("connections", [])

        total_len = start_idx + len(connections)
        logger.debug("Page: %d (%d-%d contacts)", page_count, start_idx, total_len)

        yield from connections

        next_page_token = results.get("nextPageToken")
        if next_page_token is None:
            break

        start_idx = total_len
        page_count += 1


def _get_us_mobile_number(contact: dict[str, Any]) -> str | None:
    mobile_number = None
    for number in contact.get("phoneNumbers", []):
        if number.get("type") != "mobile" or (
            mobile_number and not number.get("metadata", {}).get("sourcePrimary", False)
        ):
            continue
        contact_number = number.get("canonicalForm") or number["value"].replace(" ", "")
        if utils.is_us_phone_number(contact_number):
            mobile_number = contact_number

    return mobile_number


def _get_name(contact: dict[str, Any]) -> tuple[str, str] | None:
    if "names" not in contact:
        return None

    given_name, display_name = next(
        ((n.get("givenName"), n.get("displayName")) for n in contact["names"]),
        (None, None),
    )

    if display_name is None:
        return None

    if given_name is None:
        given_name = display_name[: display_name.find(" ")]
        logger.warning("Defaulting %s (no given name) from %s.", given_name, display_name)

    return given_name.strip(), display_name.strip()


def _get_today() -> datetime.date:
    return datetime.datetime.now(tz=datetime.UTC).date()


def _convert_date(date: dict[str, int]) -> datetime.date:
    if "year" not in date:
        logger.debug("year is not present in %s", date)

    return datetime.date(date.get("year", _get_today().year), date["month"], date["day"])


def _get_dates(contact: dict[str, Any]) -> list[models.DateTuple]:
    results: list[models.DateTuple] = []

    results.extend(
        models.DateTuple(models.DateType.BIRTHDAY, _convert_date(bd["date"]))
        for bd in contact.get("birthdays", [])
        if "date" in bd and bd.get("metadata", {}).get("primary", False)
    )

    results.extend(
        models.DateTuple(models.DateType.ANNIVERSARY, _convert_date(e["date"]))
        for e in contact.get("events", [])
        if e["type"] == "anniversary"
    )

    return results


def get_contacts(credentials_file: Path, token_file: Path) -> Iterable[models.Contact]:
    while True:
        try:
            service = _create_service(credentials_file, token_file)
            contacts = _get_contacts(service, constants.FIELDS)
            for contact in contacts:
                name = _get_name(contact)
                if name is None:
                    continue

                given_name, display_name = name
                logger.debug("Processing %s...", display_name)

                mobile_number = _get_us_mobile_number(contact)
                if mobile_number is None:
                    continue

                dates = _get_dates(contact)
                if not dates:
                    continue

                assert utils.is_us_phone_number(mobile_number)

                yield models.Contact(given_name, display_name, mobile_number, dates)

            break

        except google.auth.exceptions.RefreshError:
            logger.exception("Token failed to be refreshed", exc_info=False)
            token_file.unlink()

        except HttpError:
            logger.exception("An error occurred")
            token_file.unlink()
