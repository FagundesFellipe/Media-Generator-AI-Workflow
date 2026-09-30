"""Parsing, formatting, and semantic-version bumping for prompts."""

import re
from typing import Any


def parse_version_number_to_tuple(version_str: str) -> tuple[int, int, int]:
    """Parse a version string into a ``(major, minor, patch)`` tuple.

    Accepts an optional ``v`` prefix, e.g. ``"v1.2.3"`` or ``"1.2.3"``.

    Args:
        version_str: The version string to parse.

    Returns:
        The ``(major, minor, patch)`` integers.

    Raises:
        ValueError: If ``version_str`` does not match the expected ``X.Y.Z`` pattern.
    """
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def format_version(major: int, minor: int, patch: int) -> str:
    """Format a ``(major, minor, patch)`` triple as a version string.

    Args:
        major: Major version number.
        minor: Minor version number.
        patch: Patch version number.

    Returns:
        The formatted version string, e.g. ``"v1.2.3"``.
    """
    return f"v{major}.{minor}.{patch}"


def parse_all_versions_to_tuples(existing_versions: list[str]):
    """Parse version strings into ``(major, minor, patch)`` tuples.

    Invalid version strings are silently skipped.

    Args:
        existing_versions: Version strings to parse.

    Returns:
        A list of parsed ``(major, minor, patch)`` tuples, or the string
        ``"v1.0.0"`` if none of the inputs are valid. The mixed return type is
        inconsistent; callers must handle both cases.
    """

    versions = []

    for existing_version in existing_versions:
        try:
            parsed = parse_version_number_to_tuple(existing_version)
            versions.append(parsed)
        except ValueError:
            continue

    if not versions:
        return "v1.0.0"

    return versions


def get_last_version(parsed_versions: list[Any]) -> tuple[int, int, int]:
    """Return the highest version from a list of ``(major, minor, patch)`` tuples.

    Args:
        parsed_versions: Parsed version tuples; must be non-empty.

    Returns:
        The greatest ``(major, minor, patch)`` tuple.
    """

    latest_version = max(parsed_versions)
    return latest_version


def get_next_version(existing_versions: list[str], change_type: str = "patch") -> str:
    """Compute the next version from the existing versions and a bump type.

    Args:
        existing_versions: Version strings already in use.
        change_type: One of ``"major"``, ``"minor"``, or ``"patch"`` (default).

    Returns:
        The next version string, or ``"v1.0.0"`` if no valid version is found.
    """
    if not existing_versions:
        return "v1.0.0"

    parsed_versions = parse_all_versions_to_tuples(existing_versions)

    major, minor, patch = get_last_version(parsed_versions)

    if change_type == "major":
        return format_version(major + 1, 0, 0)
    elif change_type == "minor":
        return format_version(major, minor + 1, 0)
    else:
        return format_version(major, minor, patch + 1)
