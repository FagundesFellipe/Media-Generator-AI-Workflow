"""Unit tests for prompt-version queries."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "src"))

from prompts_manager.backend import version_queries
from prompts_manager.shared import prompts_directory


@pytest.fixture
def prompts_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point version queries at an isolated on-disk prompt store."""
    monkeypatch.setattr(prompts_directory, "PROMPTS_DIR", tmp_path)
    monkeypatch.setattr(prompts_directory, "METADATA_FILE", tmp_path / "metadata.json")
    return tmp_path


def test_get_all_versions_returns_prompt_records_newest_first(
    prompts_storage: Path,
) -> None:
    # Arrange
    prompt_dir = prompts_storage / "linkedin_post"
    prompt_dir.mkdir()
    old_version = {"prompt_version": "v1.0.0", "created_at": "2026-01-10T10:00:00Z"}
    newest_version = {
        "prompt_version": "v1.1.0",
        "created_at": "2026-02-10T10:00:00Z",
    }
    (prompt_dir / "v1.0.0.json").write_text(json.dumps(old_version))
    (prompt_dir / "v1.1.0.json").write_text(json.dumps(newest_version))

    # Act
    result = version_queries.get_all_versions("linkedin_post")

    # Assert
    assert result == [newest_version, old_version]


def test_get_all_versions_returns_an_empty_list_when_the_prompt_does_not_exist(
    prompts_storage: Path,
) -> None:
    # Arrange
    prompt_name = "missing_prompt"

    # Act
    result = version_queries.get_all_versions(prompt_name)

    # Assert
    assert result == []
