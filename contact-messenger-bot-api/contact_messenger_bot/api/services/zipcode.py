from __future__ import annotations

import contextlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Self

import pytz
import requests
from requests.adapters import HTTPAdapter
from timezonefinder import TimezoneFinder
from urllib3 import Retry

from contact_messenger_bot.api.models import Coordinate, Country

if TYPE_CHECKING:
    import datetime
    from os import PathLike
    from types import TracebackType

logger = logging.getLogger(__name__)


class ZipCode:
    """
    Responsible for translating a zip code into a Time Zone.

    Example usage:
    >> with ZipCode(Path.cwd() / "zipcode.json") as zipcode:
    >>    zipcode.get_timezone("US", "10022")
    America/New_York
    """

    def __init__(self, cache_file: PathLike | None = None, retry_count: int = 3) -> None:
        self._cache_file = Path(cache_file) if cache_file is not None else None
        self._cache: dict[tuple[Country, str], datetime.tzinfo | None] = self._load_cache(self._cache_file)
        self._timezone_finder = TimezoneFinder()
        self._sesson = self._create_session(retry_count=retry_count)
        self._is_dirty = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: object,
        exc_tb: TracebackType | None,
    ) -> None:
        self._sesson.close()
        self.save()

    @property
    def is_dirty(self) -> bool:
        """Gets a value indicating whether this instance has changes."""
        return self._is_dirty

    def get_timezone(self, country: str | Country, zip_code: str) -> datetime.tzinfo | None:
        """Looks up the timezone based on country and zip code."""
        country = Country(country)
        key = (country, zip_code)
        if key in self._cache:
            tz = self._cache[key]
            logger.debug("Loaded %s for %s from cache.", tz, zip_code)
            return tz

        tz = self._lookup_timezone(country, zip_code)
        self._cache[key] = tz
        self._is_dirty = True
        return tz

    def save(self) -> None:
        """Persists changes to the cache."""
        if not self._is_dirty:
            return

        self._save_cache()
        self._is_dirty = False

    def _save_cache(self) -> None:
        if self._cache_file is None:
            return

        # Packs the cache from being a dict[tuple[str, str], datetime.tzinfo] -> dict[str, dict[str, str | None]]
        save_cache: dict[str, dict[str, str | None]] = {}
        for key, tz in self._cache.items():
            country, zip_code = key
            if country not in save_cache:
                save_cache[country.value] = {}

            save_cache[country][zip_code] = str(tz) if tz is not None else None

        logger.debug("Saving %d items into cache %s.", len(self._cache), self._cache_file)
        self._cache_file.write_text(json.dumps(save_cache))

    def _lookup_timezone(self, country: Country, zip_code: str) -> datetime.tzinfo | None:
        coordinate = self._get_coordinate(country, zip_code)
        if coordinate is None:
            return None

        with contextlib.suppress(ValueError):
            zone = self._timezone_finder.timezone_at(lat=coordinate.latitude, lng=coordinate.longitude)
            if zone is not None:
                return pytz.timezone(zone)

        logger.warning("No timezone found for zip-code: %s, coordinate: %s.", zip_code, coordinate)
        return None

    def _get_coordinate(
        self, country: Country, zip_code: str, timeout: float | tuple[float, float] | tuple[float, None] | None = None
    ) -> Coordinate | None:
        """
        Gets the coordinate for the zip code

        :param country: The country
        :param zip_code: The zip code
        :param timeout: The optional timeout.
        :return: The Coordinate of the zip code or None if not found.
        """
        zip_code = zip_code.split("-")[0]  # in case the zip code has an extra 4 digits
        url = f"https://api.zippopotam.us/{country.value.lower()}/{zip_code}"
        response = self._sesson.get(url, timeout=timeout)
        if not response.ok:
            logger.warning("No coordinate found for %s.", zip_code)
            return None

        places = response.json().get("places", [])
        locations = (Coordinate(float(place["latitude"]), float(place["longitude"])) for place in places)
        coordinate = next(locations, None)
        if coordinate is None:
            logger.warning("No coordinate found for %s.", zip_code)
        return coordinate

    @staticmethod
    def _load_cache(cache_file: Path | None) -> dict[tuple[Country, str], datetime.tzinfo | None]:
        cache: dict[tuple[Country, str], datetime.tzinfo | None] = {}
        if cache_file is None:
            return cache

        if not cache_file.exists():
            return cache

        logger.debug("Loading %s", cache_file)
        save_cache = json.loads(cache_file.read_text())
        for country, country_map in save_cache.items():
            for zip_code, tz in country_map.items():
                key = Country(country), zip_code
                cache[key] = pytz.timezone(tz) if tz is not None else None

        logger.debug("Read %d entries from %s.", len(cache), cache_file)
        return cache

    @staticmethod
    def _create_session(retry_count: int = 3) -> requests.Session:
        s = requests.Session()
        retries = Retry(
            total=retry_count,
            backoff_factor=0.1,
        )
        adapter = HTTPAdapter(max_retries=retries)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        return s
