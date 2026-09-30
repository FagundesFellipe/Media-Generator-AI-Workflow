"""Unit tests for prompt version persistence and activation."""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "src"))

from prompts_manager.backend import metadata_store, prompt_reads, prompt_store
from prompts_manager.shared import prompts_directory


@pytest.fixture
def prompts_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    metadata_file = tmp_path / "metadata.json"
    monkeypatch.setattr(prompts_directory, "PROMPTS_DIR", tmp_path)
    monkeypatch.setattr(prompts_directory, "METADATA_FILE", metadata_file)
    monkeypatch.setattr(prompt_reads, "METADATA_FILE", metadata_file)
    monkeypatch.setattr(metadata_store, "METADATA_FILE", metadata_file)
    return tmp_path


def test_write_version_file_persists_the_complete_version_record(
    tmp_path: Path,
) -> None:
    prompt_store.write_version_file(
        tmp_path,
        "linkedin_post",
        "v1.2.3",
        "Write a concise post.",
        "openai/gpt-5",
        0.2,
        "medium",
        "fellipe",
        "Tighten the opening hook.",
    )

    version_data = json.loads((tmp_path / "v1.2.3.json").read_text())

    assert version_data == {
        "prompt_name": "linkedin_post",
        "prompt_version": "v1.2.3",
        "prompt_content": "Write a concise post.",
        "llm_model": "openai/gpt-5",
        "llm_temperature": 0.2,
        "llm_reasoning_effort": "medium",
        "owner": "fellipe",
        "change_note": "Tighten the opening hook.",
        "created_at": version_data["created_at"],
        "status": "active",
    }
    assert datetime.fromisoformat(version_data["created_at"]).utcoffset() is not None


def test_switch_active_version_registers_the_first_version(
    prompts_storage: Path,
) -> None:
    prompt_store.switch_active_version(prompts_storage, "linkedin_post", "v1.0.0")

    metadata = json.loads((prompts_storage / "metadata.json").read_text())
    assert metadata == {"active_versions": {"linkedin_post": "v1.0.0"}}


def test_switch_active_version_deprecates_the_previous_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    old_version = {"prompt_version": "v1.0.0", "status": "active"}
    saved_metadata: list[dict] = []
    monkeypatch.setattr(
        prompt_store,
        "load_metadata",
        lambda: {prompt_store.ACTIVE_VERSIONS_KEY: {"linkedin_post": "v1.0.0"}},
    )
    monkeypatch.setattr(prompt_store, "load_prompt_version", lambda *_: old_version)
    monkeypatch.setattr(prompt_store, "save_metadata", saved_metadata.append)

    prompt_store.switch_active_version(tmp_path, "linkedin_post", "v1.1.0")

    assert json.loads((tmp_path / "v1.0.0.json").read_text()) == {
        "prompt_version": "v1.0.0",
        "status": "deprecated",
    }
    assert saved_metadata == [
        {prompt_store.ACTIVE_VERSIONS_KEY: {"linkedin_post": "v1.1.0"}}
    ]


def test_switch_active_version_does_not_rewrite_the_current_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        prompt_store,
        "load_metadata",
        lambda: {prompt_store.ACTIVE_VERSIONS_KEY: {"linkedin_post": "v1.0.0"}},
    )
    monkeypatch.setattr(
        prompt_store,
        "load_prompt_version",
        lambda *_: pytest.fail("The current version should not be loaded."),
    )
    saved_metadata: list[dict] = []
    monkeypatch.setattr(prompt_store, "save_metadata", saved_metadata.append)

    prompt_store.switch_active_version(tmp_path, "linkedin_post", "v1.0.0")

    assert saved_metadata == [
        {prompt_store.ACTIVE_VERSIONS_KEY: {"linkedin_post": "v1.0.0"}}
    ]
    assert list(tmp_path.iterdir()) == []


def test_validate_prompt_size_uses_utf8_byte_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompt_store, "MAX_PROMPT_SIZE", 4)

    prompt_store.validate_prompt_size("éé")

    with pytest.raises(ValueError, match="4 bytes"):
        prompt_store.validate_prompt_size("ééa")


def test_create_prompt_version_persists_and_activates_the_first_version(
    prompts_storage: Path,
) -> None:
    created_version = prompt_store.create_prompt_version(
        "linkedin_post",
        "Write a concise post.",
        "openai/gpt-5",
        "fellipe",
        "Tighten the opening hook.",
        change_type="minor",
        temperature=0.2,
        reasoning_effort="medium",
    )

    assert created_version == "v1.0.0"
    version_data = json.loads(
        (prompts_storage / "linkedin_post" / "v1.0.0.json").read_text()
    )
    metadata = json.loads((prompts_storage / "metadata.json").read_text())
    assert version_data["prompt_content"] == "Write a concise post."
    assert version_data["status"] == "active"
    assert metadata == {"active_versions": {"linkedin_post": "v1.0.0"}}


def test_create_prompt_version_rejects_oversized_content_without_a_version_file(
    monkeypatch: pytest.MonkeyPatch, prompts_storage: Path
) -> None:
    monkeypatch.setattr(prompt_store, "MAX_PROMPT_SIZE", 4)

    with pytest.raises(ValueError, match="4 bytes"):
        prompt_store.create_prompt_version(
            "linkedin_post",
            "ééa",
            "openai/gpt-5",
            "fellipe",
            "Tighten the opening hook.",
        )

    assert not (prompts_storage / "linkedin_post" / "v1.0.0.json").exists()
    assert json.loads((prompts_storage / "metadata.json").read_text()) == {
        "active_versions": {}
    }
