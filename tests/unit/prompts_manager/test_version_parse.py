"""Unit tests for prompt semantic-version helpers."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "src"))

from prompts_manager.backend import version_parse


def test_parse_version_number_to_tuple_accepts_versions_with_or_without_prefix() -> (
    None
):
    # Arrange
    prefixed_version = "v1.2.3"
    unprefixed_version = "1.2.3"

    # Act
    prefixed_result = version_parse.parse_version_number_to_tuple(prefixed_version)
    unprefixed_result = version_parse.parse_version_number_to_tuple(unprefixed_version)

    # Assert
    assert prefixed_result == (1, 2, 3)
    assert unprefixed_result == (1, 2, 3)


def test_parse_version_number_to_tuple_rejects_an_invalid_format() -> None:
    # Arrange
    invalid_version = "release-one"

    # Act / Assert
    with pytest.raises(ValueError, match="Invalid version format"):
        version_parse.parse_version_number_to_tuple(invalid_version)


def test_format_version_returns_a_prefixed_semantic_version() -> None:
    # Arrange
    version_numbers = (2, 5, 7)

    # Act
    result = version_parse.format_version(*version_numbers)

    # Assert
    assert result == "v2.5.7"


def test_parse_all_versions_to_tuples_ignores_invalid_versions() -> None:
    # Arrange
    versions = ["v1.0.0", "not-a-version", "v2.3.4"]

    # Act
    result = version_parse.parse_all_versions_to_tuples(versions)

    # Assert
    assert result == [(1, 0, 0), (2, 3, 4)]


def test_get_next_version_increments_the_highest_semantic_version_by_change_type() -> (
    None
):
    # Arrange
    versions = ["v1.9.9", "v2.3.4", "v1.10.0"]

    # Act
    result = version_parse.get_next_version(versions, change_type="minor")

    # Assert
    assert result == "v2.4.0"


def test_get_next_version_returns_the_initial_version_for_an_empty_history() -> None:
    # Arrange
    versions: list[str] = []

    # Act
    result = version_parse.get_next_version(versions)

    # Assert
    assert result == "v1.0.0"
