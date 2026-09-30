"""Unit tests for prompt metadata persistence."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "src"))

from prompts_manager.backend import metadata_store
from prompts_manager.shared import prompts_directory


@pytest.fixture
def metadata_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point metadata operations at an isolated temporary file."""
    path = tmp_path / "metadata.json"
    monkeypatch.setattr(prompts_directory, "PROMPTS_DIR", tmp_path)
    monkeypatch.setattr(prompts_directory, "METADATA_FILE", path)
    monkeypatch.setattr(metadata_store, "METADATA_FILE", path)
    return path


def test_load_metadata_creates_and_returns_an_empty_active_versions_mapping(
    metadata_file: Path,
) -> None:
    # Arrange
    expected_metadata = {"active_versions": {}}

    # Act
    result = metadata_store.load_metadata()

    # Assert
    assert result == expected_metadata
    assert json.loads(metadata_file.read_text()) == expected_metadata


def test_save_metadata_replaces_existing_file_contents(metadata_file: Path) -> None:
    # Arrange
    metadata_file.write_text(
        json.dumps({"active_versions": {"linkedin_post": "v12.34.56"}})
    )
    updated_metadata = {"active_versions": {"linkedin_post": "v1.0.0"}}

    # Act
    metadata_store.save_metadata(updated_metadata)

    # Assert
    assert json.loads(metadata_file.read_text()) == updated_metadata
