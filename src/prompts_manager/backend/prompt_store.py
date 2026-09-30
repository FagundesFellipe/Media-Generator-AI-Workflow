"""File-based storage for prompts with semantic versioning.

Prompts are stored as JSON files in a directory structure organized by prompt
name. Each prompt directory holds one JSON file per version, and a
``metadata.json`` file at the root tracks which version is active for each
prompt.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from ..shared.prompts_directory import ensure_prompts_dir_exists, get_prompt_dir
from ..shared.settings import ACTIVE_VERSIONS_KEY, settings
from . import version_parse
from .metadata_store import load_metadata, save_metadata
from .prompt_reads import list_versions, load_prompt_version

MAX_PROMPT_SIZE = settings.max_prompt_size


def write_version_file(
    prompt_dir: Path,
    prompt_name: str,
    prompt_version: str,
    prompt_content: str,
    llm_model: str,
    llm_temperature: float | None,
    llm_reasoning_effort: str | None,
    owner: str,
    change_note: str,
) -> None:
    """Write the JSON file for a single prompt version into the prompt directory.

    Args:
        prompt_dir: Directory that holds the prompt's version files.
        prompt_name: Name of the prompt.
        prompt_version: Version string to write, e.g. ``"v1.2.3"``.
        prompt_content: Prompt text to store.
        llm_model: LLM model associated with this version.
        llm_temperature: Sampling temperature, or ``None`` if unset.
        llm_reasoning_effort: Reasoning-effort setting, or ``None`` if unset.
        owner: Author of the change.
        change_note: Short description of what changed.
    """
    prompts_data = {
        "prompt_name": prompt_name,
        "prompt_version": prompt_version,
        "prompt_content": prompt_content,
        "llm_model": llm_model,
        "llm_temperature": llm_temperature,
        "llm_reasoning_effort": llm_reasoning_effort,
        "owner": owner,
        "change_note": change_note,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "active",
    }

    version_file = prompt_dir / f"{prompt_version}.json"
    with open(version_file, "w") as file:
        json.dump(prompts_data, file, indent=2, ensure_ascii=False)


def switch_active_version(
    prompt_dir: Path, prompt_name: str, prompt_version: str
) -> None:
    """Mark ``prompt_version`` as active and deprecate the previous active version.

    Args:
        prompt_dir: Directory that holds the prompt's version files.
        prompt_name: Name of the prompt.
        prompt_version: Version to promote as active.
    """
    metadata = load_metadata()
    if prompt_name not in metadata[ACTIVE_VERSIONS_KEY]:
        metadata[ACTIVE_VERSIONS_KEY][prompt_name] = prompt_version
    else:
        version_active = metadata[ACTIVE_VERSIONS_KEY][prompt_name]
        if prompt_version != version_active:
            old_version_data = load_prompt_version(prompt_name, version_active)
            if old_version_data:
                old_version_data["status"] = "deprecated"
                old_file = prompt_dir / f"{version_active}.json"
                with open(old_file, "w") as file:
                    json.dump(old_version_data, file, indent=2, ensure_ascii=False)

        metadata[ACTIVE_VERSIONS_KEY][prompt_name] = prompt_version

    save_metadata(metadata)


def validate_prompt_size(prompt_content: str) -> None:
    """Raise ``ValueError`` if the content exceeds the maximum allowed size.

    Args:
        prompt_content: Prompt text to validate.

    Raises:
        ValueError: If the UTF-8 encoded content is larger than ``MAX_PROMPT_SIZE``.
    """
    if len(prompt_content.encode("utf-8")) > MAX_PROMPT_SIZE:
        raise ValueError(
            f"Prompt content exceeds maximum size of {MAX_PROMPT_SIZE:,} bytes"
        )


def create_prompt_version(
    prompt_name: str,
    prompt_content: str,
    model: str,
    owner: str,
    change_note: str,
    change_type: str = "patch",
    temperature: float | None = None,
    reasoning_effort: str | None = None,
) -> str:
    """Create a new prompt version and make it the active one.

    The previously active version is automatically marked as deprecated.

    Args:
        prompt_name: Name of the prompt.
        prompt_content: Prompt text to store.
        model: LLM model associated with this version.
        owner: Author of the change.
        change_note: Short description of what changed.
        change_type: Version bump to apply: ``"major"``, ``"minor"``, or
            ``"patch"`` (default).
        temperature: Sampling temperature, or ``None`` if unset.
        reasoning_effort: Reasoning-effort setting, or ``None`` if unset.

    Returns:
        The newly created version string.
    """
    ensure_prompts_dir_exists()

    prompt_dir = get_prompt_dir(prompt_name)
    prompt_dir.mkdir(exist_ok=True)

    existing_versions = list_versions(prompt_name)
    prompt_version = version_parse.get_next_version(existing_versions, change_type)

    validate_prompt_size(prompt_content)

    write_version_file(
        prompt_dir,
        prompt_name,
        prompt_version,
        prompt_content,
        model,
        temperature,
        reasoning_effort,
        owner,
        change_note,
    )
    switch_active_version(prompt_dir, prompt_name, prompt_version)

    return prompt_version
