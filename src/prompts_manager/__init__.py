"""Prompts manager.

A single-user tool for storing, versioning, and serving prompt templates.
The storage backend lives in :mod:`prompts_manager.backend`; the Flask web
interface lives in :mod:`prompts_manager.frontend`.
"""

from prompts_manager.backend import (
    VERSION_FILE_SUFFIX,
    create_prompt_version,
    deprecate_version,
    get_active_version,
    get_all_versions,
    list_versions,
    load_metadata,
    load_prompt_version,
    save_metadata,
    set_active_version,
    switch_active_version,
    validate_prompt_size,
    write_version_file,
)

__all__ = [
    "VERSION_FILE_SUFFIX",
    "create_prompt_version",
    "deprecate_version",
    "get_active_version",
    "get_all_versions",
    "list_versions",
    "load_metadata",
    "load_prompt_version",
    "save_metadata",
    "set_active_version",
    "switch_active_version",
    "validate_prompt_size",
    "write_version_file",
]
