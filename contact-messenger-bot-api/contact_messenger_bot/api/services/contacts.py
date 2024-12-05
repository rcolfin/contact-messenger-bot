from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any, Final, cast

import backoff
import google.auth.exceptions
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from contact_messenger_bot.api import constants, models, utils

if TYPE_CHECKING:
    from collections.abc import Iterable

    from contact_messenger_bot.api import oauth2
    from contact_messenger_bot.api.services.zipcode import ZipCode


logger = logging.getLogger(__name__)


class Contacts:
    SCOPES: Final[list[str]] = ["https://www.googleapis.com/auth/contacts.readonly"]
    FIELDS: Final[str] = (
        "names,emailAddresses,phoneNumbers,birthdays,events,userDefined,addresses"  # see https://developers.google.com/people/api/rest/v1/people
    )
    PEOPLE_API_RESOURCE: Final[str] = "people/me"
    MAX_PAGE_SIZE: Final[int] = 10

    def __init__(self, creds: oauth2.CredentialsManager, zipcode: ZipCode) -> None:
        self.creds = creds
        self.zipcode = zipcode

    def get_contacts(self) -> Iterable[models.Contact]:
        while True:
            try:
                service = self._create_service()
                contacts = self._get_contacts(service, self.FIELDS)
                for contact in contacts:
                    name = self._get_name(contact)
                    if name is None:
                        continue

                    given_name, display_name = name
                    logger.debug("Processing %s...", display_name)

                    home_postal_code = self._get_home_postal_code(contact)
                    mobile_number = self._get_us_mobile_number(contact)
                    if mobile_number is None:
                        continue

                    dates = self._get_dates(contact)
                    if not dates:
                        continue

                    assert utils.is_us_phone_number(mobile_number)

                    tz = self.zipcode.get_timezone(models.Country.US, home_postal_code) if home_postal_code else None
                    yield models.Contact(given_name, display_name, mobile_number, dates, home_postal_code, tz)

                break

            except google.auth.exceptions.RefreshError:
                logger.exception("Token failed to be refreshed", exc_info=False)
                self.creds.invalidate_token()

            except HttpError:
                logger.exception("An error occurred")
                self.creds.invalidate_token()

    @backoff.on_exception(backoff.expo, AttributeError, max_tries=constants.MAX_RETRY)
    def _create_service(self) -> Resource:
        return build(
            "people", "v1", credentials=self.creds.create_oauth_credentials(self.SCOPES), cache_discovery=False
        )

    def _get_contacts(self, service: Resource, fields: str) -> Iterable[dict[str, Any]]:
        # Call the People API
        next_page_token = None
        start_idx = 0
        page_count = 1
        while True:
            request = (
                service.people()
                .connections()
                .list(
                    resourceName=self.PEOPLE_API_RESOURCE,
                    pageSize=self.MAX_PAGE_SIZE,
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

    def _get_us_mobile_number(self, contact: dict[str, Any]) -> str | None:
        mobile_number = None
        for number in contact.get("phoneNumbers", []):
            if number.get("type") != "mobile" or (
                mobile_number and not number.get("metadata", {}).get("sourcePrimary", False)
            ):
                continue

            contact_number = number.get("canonicalForm")
            if contact_number is None:
                display_name = cast(tuple[str, str], self._get_name(contact))[1]
                logger.warning("%s has no canonical phone number.", display_name)
                return number["value"].replace(" ", "")

            if utils.is_us_phone_number(contact_number):
                mobile_number = contact_number

        return mobile_number

    def _get_home_postal_code(self, contact: dict[str, Any]) -> str | None:
        home_addresses = (
            address.get("postalCode")
            for address in contact.get("addresses", [])
            if address.get("postalCode") and address.get("type") == "home"
        )
        return next(home_addresses, None)

    def _get_name(self, contact: dict[str, Any]) -> tuple[str, str] | None:
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

    def _convert_date(self, date: dict[str, int]) -> datetime.date:
        year = date.get("year")
        if year is None:
            logger.debug("year is not present in %s", date)
            year = constants.TODAY.year

        return datetime.date(year, date["month"], date["day"])

    def _get_dates(self, contact: dict[str, Any]) -> list[models.DateTuple]:
        results: list[models.DateTuple] = []

        results.extend(
            models.DateTuple(models.DateType.BIRTHDAY, self._convert_date(bd["date"]))
            for bd in contact.get("birthdays", [])
            if "date" in bd and bd.get("metadata", {}).get("primary", False)
        )

        results.extend(
            models.DateTuple(models.DateType.ANNIVERSARY, self._convert_date(e["date"]))
            for e in contact.get("events", [])
            if e["type"] == "anniversary"
        )

        return results
