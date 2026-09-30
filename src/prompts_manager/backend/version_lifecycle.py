"""State transitions for prompt versions (active ↔ deprecated)."""

import json

from ..shared.prompts_directory import ensure_prompts_dir_exists, get_prompt_dir
from ..shared.settings import ACTIVE_VERSIONS_KEY
from .metadata_store import load_metadata, save_metadata
from .prompt_reads import load_prompt_version


def get_active_version(prompt_name: str) -> str | None:
    """Return the currently active version of a prompt.

    Args:
        prompt_name: Name of the prompt.

    Returns:
        The active version string, or ``None`` if none is set.
    """
    metadata = load_metadata()
    return metadata[ACTIVE_VERSIONS_KEY].get(prompt_name)


def set_active_version(prompt_name: str, version: str) -> bool:
    """Make a specific version the active one for a prompt.

    The previously active version is marked as deprecated.

    Args:
        prompt_name: Name of the prompt.
        version: Version to promote as active.

    Returns:
        ``True`` on success, or ``False`` if the requested version does not exist.
    """
    ensure_prompts_dir_exists()

    version_data = load_prompt_version(prompt_name, version)
    if not version_data:
        return False

    metadata = load_metadata()

    old_version = metadata[ACTIVE_VERSIONS_KEY].get(prompt_name)

    if old_version and old_version != version:
        old_data = load_prompt_version(prompt_name, old_version)
        if old_data:
            old_data["status"] = "deprecated"
            old_file = get_prompt_dir(prompt_name) / f"{old_version}.json"
            with open(old_file, "w") as file:
                json.dump(old_data, file, indent=2, ensure_ascii=False)

    version_data["status"] = "active"
    version_file = get_prompt_dir(prompt_name) / f"{version}.json"
    with open(version_file, "w") as file:
        json.dump(version_data, file, indent=2, ensure_ascii=False)

    metadata[ACTIVE_VERSIONS_KEY][prompt_name] = version
    save_metadata(metadata)
    return True


def deprecate_version(prompt_name: str, version: str) -> bool:
    """Mark a version as deprecated without changing the active version.

    The currently active version cannot be deprecated directly.

    Args:
        prompt_name: Name of the prompt.
        version: Version to deprecate.

    Returns:
        ``True`` on success, or ``False`` if the version does not exist or is
        currently active.
    """
    ensure_prompts_dir_exists()

    version_data = load_prompt_version(prompt_name, version)
    if not version_data:
        return False

    metadata = load_metadata()
    if metadata[ACTIVE_VERSIONS_KEY].get(prompt_name) == version:
        return False

    version_data["status"] = "deprecated"
    version_file = get_prompt_dir(prompt_name) / f"{version}.json"

    with open(version_file, "w") as file:
        json.dump(version_data, file, indent=2, ensure_ascii=False)

    return True
