"""Read and write the prompts ``metadata.json`` file."""

import fcntl
import json

from ..shared.prompts_directory import ensure_prompts_dir_exists
from ..shared.settings import ACTIVE_VERSIONS_KEY, METADATA_FILE


def load_metadata() -> dict:
    """Load and return the metadata dictionary from ``metadata.json``.

    Returns:
        The metadata dictionary, or the default ``{"active_versions": {}}``
        structure if the file does not exist.
    """
    ensure_prompts_dir_exists()

    if not METADATA_FILE.exists():
        return {ACTIVE_VERSIONS_KEY: {}}
    with open(METADATA_FILE) as file:
        return json.load(file)


def save_metadata(metadata: dict):
    """Persist the metadata dictionary to ``metadata.json`` atomically.

    Acquires an exclusive file lock to avoid race conditions between
    concurrent read-modify-write cycles.

    Args:
        metadata: Metadata dictionary to persist.
    """
    ensure_prompts_dir_exists()
    with open(METADATA_FILE, "r+") as file:
        fcntl.flock(file, fcntl.LOCK_EX)
        file.seek(0)
        json.dump(metadata, file, indent=2, ensure_ascii=False)
        file.truncate()
        fcntl.flock(file, fcntl.LOCK_UN)
