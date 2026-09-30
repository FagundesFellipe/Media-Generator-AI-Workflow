"""Centralized configuration loaded from environment variables."""

from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROMPTS_MANAGER_DIR = (
    Path(__file__).resolve().parent.parent
)  # shared/ -> prompts_manager/
_SRC_DIR = _PROMPTS_MANAGER_DIR.parent  # prompts_manager/ -> src/
ENV_FILE = _PROMPTS_MANAGER_DIR / ".env"

# Anchor for relative PROMPT_DIR values. The prompts belong to the
# media_generator_graph package, so relative paths are resolved against it
# rather than the process CWD (which changes depending on where the server
# is launched from).
_PROMPTS_BASE_DIR = _SRC_DIR / "media_generator_graph"
_DEFAULT_PROMPTS_SUBDIR = Path("agents/prompts")


def _resolve_prompts_dir() -> Path:
    """Resolve the prompts directory for local dev, an installed package, or Docker.

    Returns:
        The first existing candidate directory, or the default candidate if none
        of them exist.
    """

    candidates = [
        _PROMPTS_BASE_DIR / _DEFAULT_PROMPTS_SUBDIR,
        Path("/app/backend/media_generator_graph/agents/prompts"),
        Path.cwd() / "backend/media_generator_graph/agents/prompts",
    ]

    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    return candidates[0]


def _resolve_prompt_dir(value: str) -> Path:
    """Resolve a configured ``PROMPT_DIR`` value to an absolute path.

    Absolute values are kept as-is; relative values are anchored to the
    ``media_generator_graph`` package directory so the resolved location does
    not depend on the process CWD.

    Args:
        value: Raw ``PROMPT_DIR`` value, absolute or relative.

    Returns:
        The expanded, absolute prompt directory path.
    """
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (_PROMPTS_BASE_DIR / path).resolve()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    # --- ENVIRONMENT ---
    # "development" (default) or "production"
    # In production, the synchronous webhook (webhook/sync) is disabled.
    environment_prompt_manager: str = "development"

    # --- DIRECTORY TO SAVE PROMPTS ---
    prompt_dir: str = str(_resolve_prompts_dir())

    # --- PROMPT SIZE LIMIT  ---
    max_prompt_size: int = 100_000

    # --- FRONTEND CONFIGS ---
    prompt_manager_port: int = 5000
    flask_secret_key: SecretStr | None = None
    flask_debug: bool = False

    # --- SERVER TIMEZONE ---
    prompt_manager_server_timezone: str = "UTC"

    @field_validator("prompt_dir")
    @classmethod
    def _normalize_prompt_dir(cls, value: str) -> str:
        """Anchor relative ``PROMPT_DIR`` values to a CWD-independent base.

        Args:
            value: Raw ``PROMPT_DIR`` value from the environment or default.

        Returns:
            The absolute prompt directory path as a string.
        """
        return str(_resolve_prompt_dir(value))


settings = Settings()

PROMPTS_DIR = Path(settings.prompt_dir)
METADATA_FILE = PROMPTS_DIR / "metadata.json"
ACTIVE_VERSIONS_KEY = "active_versions"
