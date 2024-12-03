from __future__ import annotations

import logging
import sys
import tempfile
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Callable, TypeVar

from google.cloud import storage

from . import constants, gcs

if TYPE_CHECKING:
    import flask

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

RetType = TypeVar("RetType")


def authenticated(
    func: Callable[[flask.Request, Path | None, Path | None], RetType],
) -> Callable[[flask.Request], RetType]:
    client = storage.Client()

    bucket = client.get_bucket(constants.GCS_BUCKET)

    @wraps(func)
    def with_credentials(request: flask.Request) -> RetType:
        with (
            tempfile.TemporaryDirectory() as temp,
            gcs.download(Path(temp), bucket, constants.CREDENTIALS_FILE) as credentials_file,
            gcs.download(Path(temp), bucket, constants.TOKEN_FILE) as token_file,
        ):
            return func(request, credentials_file, token_file)

    return with_credentials
