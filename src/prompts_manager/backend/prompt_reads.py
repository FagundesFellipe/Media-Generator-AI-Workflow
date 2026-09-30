"""Read prompt versions stored on disk."""

import json

from ..shared.prompts_directory import ensure_prompts_dir_exists, get_prompt_dir
from ..shared.settings import ACTIVE_VERSIONS_KEY, METADATA_FILE, PROMPTS_DIR
from . import version_parse
from .metadata_store import load_metadata

VERSION_FILE_SUFFIX = ".json"


def list_prompts() -> list[str]:
    """Returns a list of all prompts names.

    Subdirectories within the root of prompts, excluding ``. git``.
    """
    ensure_prompts_dir_exists()

    if not PROMPTS_DIR:
        return []

    return [d.name for d in PROMPTS_DIR.iterdir() if d.is_dir() and d.name != ".git"]


def list_versions(prompt_name: str) -> list[str]:
    """Return the available versions of a prompt, oldest to newest.

    Args:
        prompt_name: Name of the prompt.

    Returns:
        Version strings sorted ascending by semantic version. The
        ``metadata.json`` file is excluded.
    """
    prompt_dir = get_prompt_dir(prompt_name)

    if not prompt_dir.exists():
        return []

    version_names = []
    for json_file in prompt_dir.glob(f"*{VERSION_FILE_SUFFIX}"):
        if json_file.name != METADATA_FILE.name:
            version_names.append(json_file.stem)

    try:
        return sorted(
            version_names,
            key=lambda version: version_parse.parse_version_number_to_tuple(version),
        )
    except ValueError:
        return sorted(version_names)


def load_prompt_version(prompt_name: str, version: str | None = None) -> dict | None:
    """Load and return the JSON data for a specific prompt version.

    If no version is given, the active version from the metadata is used,
    falling back to the most recent available version.

    Args:
        prompt_name: Name of the prompt.
        version: Version to load, or ``None`` to resolve it automatically.

    Returns:
        The parsed version data, or ``None`` if the prompt or version is missing.
    """
    ensure_prompts_dir_exists()

    if version is None:
        metadata = load_metadata()
        version = metadata[ACTIVE_VERSIONS_KEY].get(prompt_name)

        if not version:
            versions = list_versions(prompt_name)
            if not versions:
                return None
            version = versions[-1]

    version_file = get_prompt_dir(prompt_name) / f"{version}{VERSION_FILE_SUFFIX}"

    if not version_file.exists():
        return None

    with open(version_file) as file:
        return json.load(file)
