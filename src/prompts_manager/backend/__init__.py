"""Backend for the prompts manager.

File-based, semantically versioned prompt storage, plus the lifecycle
operations (activate, deprecate) and read queries over stored versions.
"""

from prompts_manager.backend.metadata_store import load_metadata, save_metadata
from prompts_manager.backend.prompt_reads import (
    VERSION_FILE_SUFFIX,
    list_versions,
    load_prompt_version,
)
from prompts_manager.backend.prompt_store import (
    create_prompt_version,
    switch_active_version,
    validate_prompt_size,
    write_version_file,
)
from prompts_manager.backend.version_lifecycle import (
    deprecate_version,
    get_active_version,
    set_active_version,
)
from prompts_manager.backend.version_queries import get_all_versions

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
