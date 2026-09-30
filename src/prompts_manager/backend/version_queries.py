"""Queries that return a prompt's versions as loaded data."""

from ..shared.prompts_directory import ensure_prompts_dir_exists
from .prompt_reads import list_versions, load_prompt_version


def get_all_versions(prompt_name: str) -> list[dict]:
    """Return all versions of a prompt as loaded JSON dictionaries.

    Args:
        prompt_name: Name of the prompt.

    Returns:
        Version dictionaries sorted by creation date, most recent first.
    """
    ensure_prompts_dir_exists()

    versions = list_versions(prompt_name)

    versions_list = []
    for version in versions:
        data = load_prompt_version(prompt_name, version)
        if data:
            versions_list.append(data)

    return sorted(versions_list, key=lambda x: x["created_at"], reverse=True)
