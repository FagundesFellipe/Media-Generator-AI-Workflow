"""Unit tests for prompt-version lifecycle transitions."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "src"))

from prompts_manager.backend import metadata_store, version_lifecycle
from prompts_manager.shared import prompts_directory


@pytest.fixture
def prompts_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point lifecycle operations at an isolated on-disk prompt store."""
    metadata_file = tmp_path / "metadata.json"
    monkeypatch.setattr(prompts_directory, "PROMPTS_DIR", tmp_path)
    monkeypatch.setattr(prompts_directory, "METADATA_FILE", metadata_file)
    monkeypatch.setattr(metadata_store, "METADATA_FILE", metadata_file)
    return tmp_path


def test_set_active_version_promotes_requested_version_and_deprecates_previous_one(
    prompts_storage: Path,
) -> None:
    # Arrange
    prompt_dir = prompts_storage / "linkedin_post"
    prompt_dir.mkdir()
    (prompt_dir / "v1.0.0.json").write_text(
        json.dumps({"prompt_version": "v1.0.0", "status": "active"})
    )
    (prompt_dir / "v1.1.0.json").write_text(
        json.dumps({"prompt_version": "v1.1.0", "status": "deprecated"})
    )
    (prompts_storage / "metadata.json").write_text(
        json.dumps({"active_versions": {"linkedin_post": "v1.0.0"}})
    )

    # Act
    result = version_lifecycle.set_active_version("linkedin_post", "v1.1.0")

    # Assert
    assert result is True
    assert (
        json.loads((prompt_dir / "v1.0.0.json").read_text())["status"] == "deprecated"
    )
    assert json.loads((prompt_dir / "v1.1.0.json").read_text())["status"] == "active"
    assert json.loads((prompts_storage / "metadata.json").read_text()) == {
        "active_versions": {"linkedin_post": "v1.1.0"}
    }


def test_set_active_version_returns_false_without_changing_metadata_when_missing(
    prompts_storage: Path,
) -> None:
    # Arrange
    metadata = {"active_versions": {"linkedin_post": "v1.0.0"}}
    (prompts_storage / "metadata.json").write_text(json.dumps(metadata))

    # Act
    result = version_lifecycle.set_active_version("linkedin_post", "v9.9.9")

    # Assert
    assert result is False
    assert json.loads((prompts_storage / "metadata.json").read_text()) == metadata


def test_deprecate_version_marks_an_inactive_version_as_deprecated(
    prompts_storage: Path,
) -> None:
    # Arrange
    prompt_dir = prompts_storage / "linkedin_post"
    prompt_dir.mkdir()
    version_file = prompt_dir / "v1.0.0.json"
    version_file.write_text(
        json.dumps({"prompt_version": "v1.0.0", "status": "active"})
    )
    (prompts_storage / "metadata.json").write_text(
        json.dumps({"active_versions": {"linkedin_post": "v1.1.0"}})
    )

    # Act
    result = version_lifecycle.deprecate_version("linkedin_post", "v1.0.0")

    # Assert
    assert result is True
    assert json.loads(version_file.read_text())["status"] == "deprecated"


def test_deprecate_version_keeps_the_active_version_unchanged(
    prompts_storage: Path,
) -> None:
    # Arrange
    prompt_dir = prompts_storage / "linkedin_post"
    prompt_dir.mkdir()
    version_file = prompt_dir / "v1.0.0.json"
    version_file.write_text(
        json.dumps({"prompt_version": "v1.0.0", "status": "active"})
    )
    (prompts_storage / "metadata.json").write_text(
        json.dumps({"active_versions": {"linkedin_post": "v1.0.0"}})
    )

    # Act
    result = version_lifecycle.deprecate_version("linkedin_post", "v1.0.0")

    # Assert
    assert result is False
    assert json.loads(version_file.read_text())["status"] == "active"
