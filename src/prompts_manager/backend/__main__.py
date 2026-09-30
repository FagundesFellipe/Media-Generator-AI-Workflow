"""Entrypoint for the prompts manager backend server.

This module performs a small set of fail-fast configuration checks before
starting the Flask application. It validates that the environment is
consistent (debug mode is never enabled in production) and that a prompt
directory has been configured, then boots the HTTP server.
"""

import os
import sys

import structlog

from prompts_manager.frontend.app import create_app
from prompts_manager.shared.settings import settings

logger = structlog.get_logger()


def check_environment_and_debug_mode() -> None:
    """Ensure debug mode is not enabled while running in production.

    Raises:
        RuntimeError: If `settings.flask_debug` is True while
            `settings.environment_prompt_manager` is "production".
    """
    if settings.flask_debug and settings.environment_prompt_manager == "production":
        raise RuntimeError("FLASK_DEBUG cannot be True in production")


def check_prompt_dir_value() -> None:
    """Resolve and validate the configured prompt directory.

    The value is read from the `PROMPT_DIR` environment variable first,
    falling back to `settings.prompt_dir`. When no value is available an
    actionable error is raised so the operator knows how to fix it, and the
    resolved path is logged on success.

    Raises:
        RuntimeError: If no prompt directory is configured.
    """
    prompt_dir = os.environ.get("PROMPT_DIR", settings.prompt_dir)

    if not prompt_dir:
        raise RuntimeError(
            "PROMPT_DIR is not set. Add it to the .env file: "
            "PROMPT_DIR=/path/to/prompts or export the variable: "
            "export PROMPT_DIR=/path/to/prompts"
        )

    logger.info("Prompt directory configured", prompt_dir=prompt_dir)


def main() -> None:
    """Validate configuration and start the prompts manager server.

    Runs the pre-flight configuration checks, exiting with status code 1 if
    any of them fail, then creates and runs the Flask application bound to
    the configured port on localhost.
    """
    try:
        check_environment_and_debug_mode()
        check_prompt_dir_value()
    except RuntimeError as e:
        logger.error("Invalid configuration", error=str(e))
        sys.exit(1)

    logger.info("Starting server", url="http://127.0.0.1:5000")
    app = create_app()
    app.run(
        debug=settings.flask_debug, port=settings.prompt_manager_port, host="127.0.0.1"
    )


if __name__ == "__main__":
    main()
