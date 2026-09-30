"""Unit tests for reading prompt versions from disk."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "src"))

from prompts_manager.backend import prompt_reads
from prompts_manager.shared import prompts_directory


@pytest.fixture
def prompts_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point prompt reads at an isolated on-disk prompt store."""
    monkeypatch.setattr(prompts_directory, "PROMPTS_DIR", tmp_path)
    monkeypatch.setattr(prompts_directory, "METADATA_FILE", tmp_path / "metadata.json")
    monkeypatch.setattr(prompt_reads, "PROMPTS_DIR", tmp_path)
    return tmp_path


def test_load_prompt_version_returns_the_requested_version_data(
    prompts_storage: Path,
) -> None:
    # Arrange
    version_data = {
        "prompt_name": "linkedin_post",
        "prompt_version": "v1.0.0",
        "prompt_content": "Write a concise post.",
    }
    version_file = prompts_storage / "linkedin_post" / "v1.0.0.json"
    version_file.parent.mkdir()
    version_file.write_text(json.dumps(version_data))

    # Act
    result = prompt_reads.load_prompt_version("linkedin_post", "v1.0.0")

    # Assert
    assert result == version_data


def test_load_prompt_version_uses_the_active_version_when_none_is_requested(
    monkeypatch: pytest.MonkeyPatch, prompts_storage: Path
) -> None:
    # Arrange
    active_version_data = {"prompt_version": "v1.1.0", "prompt_content": "Active"}
    version_file = prompts_storage / "linkedin_post" / "v1.1.0.json"
    version_file.parent.mkdir()
    version_file.write_text(json.dumps(active_version_data))
    monkeypatch.setattr(
        prompt_reads,
        "load_metadata",
        lambda: {"active_versions": {"linkedin_post": "v1.1.0"}},
    )

    # Act
    result = prompt_reads.load_prompt_version("linkedin_post")

    # Assert
    assert result == active_version_data


def test_load_prompt_version_uses_the_latest_version_when_no_active_version_exists(
    monkeypatch: pytest.MonkeyPatch, prompts_storage: Path
) -> None:
    # Arrange
    prompt_dir = prompts_storage / "linkedin_post"
    prompt_dir.mkdir()
    (prompt_dir / "v1.2.0.json").write_text(
        json.dumps({"prompt_version": "v1.2.0", "prompt_content": "Latest"})
    )
    (prompt_dir / "v1.0.0.json").write_text(
        json.dumps({"prompt_version": "v1.0.0", "prompt_content": "Old"})
    )
    (prompt_dir / "metadata.json").write_text(json.dumps({"active_versions": {}}))
    monkeypatch.setattr(prompt_reads, "load_metadata", lambda: {"active_versions": {}})

    # Act
    result = prompt_reads.load_prompt_version("linkedin_post")

    # Assert
    assert result == {"prompt_version": "v1.2.0", "prompt_content": "Latest"}


def test_load_prompt_version_returns_none_when_the_requested_version_is_missing(
    prompts_storage: Path,
) -> None:
    # Arrange
    (prompts_storage / "linkedin_post").mkdir()

    # Act
    result = prompt_reads.load_prompt_version("linkedin_post", "v9.9.9")

    # Assert
    assert result is None
