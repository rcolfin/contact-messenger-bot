import logging
from collections.abc import Generator
from contextlib import contextmanager
from functools import cache
from os import PathLike
from pathlib import Path

import google.api_core.exceptions
import google.cloud.storage as storage  # noqa: PLR0402

from contact_messenger_bot.functions import constants

logger = logging.getLogger(__name__)


@cache
def get_bucket() -> storage.Bucket:
    client = storage.Client()
    return client.bucket(constants.GCS_BUCKET)


@contextmanager
def download(dest_path: PathLike, bucket: storage.Bucket, file: str) -> Generator[Path, None, None]:
    dest_file: Path = Path(dest_path, Path(file).name).resolve()
    blob = bucket.blob(file)
    if blob is not None:
        logger.info("Downloading gs://%s/%s to %s", bucket.name, file, dest_file)
        try:
            with dest_file.open("wb") as f:
                blob.download_to_file(f)
        except google.api_core.exceptions.NotFound:
            logger.info("gs://%s/%s does not exist", bucket.name, file)
            dest_file.unlink()

    ctime = dest_file.stat().st_ctime if dest_file.exists() else None
    yield dest_file
    if dest_file.exists() and dest_file.stat().st_ctime != ctime:
        logger.info("Uploading %s to gs://%s/%s", dest_file, bucket.name, file)
        blob.upload_from_filename(dest_file)
