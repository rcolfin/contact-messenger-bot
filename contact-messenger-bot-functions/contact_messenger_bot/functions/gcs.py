import logging
import sys
from collections.abc import Generator
from contextlib import contextmanager
from os import PathLike
from pathlib import Path

from google.cloud import storage

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))


@contextmanager
def download(dest_path: PathLike, bucket: storage.Bucket, file: str) -> Generator[Path, None, None]:
    dest_file: Path = Path(dest_path, Path(file).name).resolve()
    blob = bucket.get_blob(file)
    if blob is not None:
        logger.info("Downloading gs://%s/%s to %s", bucket.name, file, dest_file)
        with dest_file.open("wb") as f:
            blob.download_to_file(f)

    ctime = dest_file.stat().st_ctime if dest_file.exists() else None
    yield dest_file
    if dest_file.exists() and dest_file.stat().st_ctime != ctime:
        logger.info("Uploading %s to gs://%s/%s", dest_file, bucket.name, file)
        blob.upload_from_filename(dest_file)
