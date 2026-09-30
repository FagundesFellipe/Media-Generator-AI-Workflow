"""Interface web Flask para gerenciamento de prompts com versionamento semântico.

Oferece páginas renderizadas no servidor para criar, visualizar, ativar
e descontinuar versões de prompts, utilizando o armazenamento baseado em arquivos.
"""

import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFProtect

from prompts_manager.backend.llm_models import OpenRouterModelsIds
from prompts_manager.backend.prompt_reads import list_prompts
from prompts_manager.backend.prompt_store import create_prompt_version
from prompts_manager.backend.version_lifecycle import (
    get_active_version,
    set_active_version,
)
from prompts_manager.backend.version_queries import get_all_versions, list_versions
from prompts_manager.shared.settings import settings


def _get_tz() -> ZoneInfo:
    try:
        return ZoneInfo(settings.prompt_manager_server_timezone)
    except (ZoneInfoNotFoundError, KeyError):
        return ZoneInfo("UTC")


def _format_datetime(iso_string: str, fmt: str = "%d/%m/%Y %H:%M") -> str:
    try:
        dt = datetime.fromisoformat(iso_string)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(_get_tz()).strftime(fmt)
    except (ValueError, TypeError):
        return iso_string


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
    )
    secret = settings.flask_secret_key
    app.secret_key = secret.get_secret_value() if secret else None

    CSRFProtect(app)

    @app.context_processor
    def _inject_template_globals():
        return {
            "model_options": [
                (model.value, model.name) for model in OpenRouterModelsIds
            ],
            "app_timezone": settings.prompt_manager_server_timezone,
        }

    def _tz_filter(iso_string: str, fmt: str = "%d/%m/%Y %H:%M") -> str:
        return _format_datetime(iso_string, fmt)

    app.jinja_env.filters["localtime"] = _tz_filter

    _validate_prompt_dir()

    # ------------------------------------------------------------------ #
    #  Início — lista de prompts + formulário de criação rápida           #
    # ------------------------------------------------------------------ #

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            if not re.match(
                r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$",
                request.form["prompt_name"].strip(),
            ):
                flash(
                    "Nome de prompt inválido. "
                    "Use apenas letras, números, hífens e underscores.",
                    "error",
                )
                return redirect(url_for("index"))
            try:
                create_prompt_version(
                    prompt_name=request.form["prompt_name"].strip(),
                    prompt_content=request.form["prompt_content"].strip(),
                    model=request.form["model"].strip(),
                    owner=request.form["owner"].strip(),
                    change_note=request.form["change_note"].strip(),
                    change_type=request.form.get("change_type", "patch"),
                    temperature=_parse_optional_float(request.form.get("temperature")),
                    reasoning_effort=request.form.get("reasoning_effort") or None,
                )
                flash(
                    f"Prompt '{request.form['prompt_name'].strip()}' criado.",
                    "success",
                )
            except ValueError as exc:
                flash(str(exc), "error")
            return redirect(url_for("index"))

        prompts_with_versions = []
        for name in list_prompts():
            prompts_with_versions.append(
                {
                    "name": name,
                    "active_version": get_active_version(name),
                    "version_count": len(list_versions(name)),
                }
            )
        return render_template("index.html", prompts=prompts_with_versions)

    # ------------------------------------------------------------------ #
    #  Detalhes do prompt — versões, criar, ativar, descontinuar          #
    # ------------------------------------------------------------------ #

    @app.route("/prompts/<name>", methods=["GET"])
    def prompt_detail(name: str):
        versions = get_all_versions(name)
        active = get_active_version(name)
        if not versions:
            flash(f"Prompt '{name}' não encontrado.", "error")
            return redirect(url_for("index"))
        return render_template(
            "prompt_detail.html",
            prompt_name=name,
            versions=versions,
            active_version=active,
        )

    @app.route("/prompts/<name>/versions", methods=["POST"])
    def create_version(name: str):
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$", name):
            flash("Nome de prompt inválido.", "error")
            return redirect(url_for("index"))
        try:
            create_prompt_version(
                prompt_name=name,
                prompt_content=request.form["prompt_content"].strip(),
                model=request.form["model"].strip(),
                owner=request.form["owner"].strip(),
                change_note=request.form["change_note"].strip(),
                change_type=request.form.get("change_type", "patch"),
                temperature=_parse_optional_float(request.form.get("temperature")),
                reasoning_effort=request.form.get("reasoning_effort") or None,
            )
            flash(f"Nova versão criada para '{name}'.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("prompt_detail", name=name))

    @app.route("/prompts/<name>/versions/<version>/activate", methods=["POST"])
    def activate_version(name: str, version: str):
        ok = set_active_version(name, version)
        if ok:
            flash(f"Versão {version} agora está ativa para '{name}'.", "success")
        else:
            flash(f"Não foi possível ativar a versão {version}.", "error")
        return redirect(url_for("prompt_detail", name=name))

    @app.route("/prompts/<name>/versions/<version>/deprecate", methods=["POST"])
    def deprecate_version(name: str, version: str):
        ok = deprecate_version(name, version)
        if ok:
            flash(f"Versão {version} descontinuada.", "success")
        else:
            flash(
                "Não é possível descontinuar a versão ativa ou versão não encontrada.",
                "error",
            )
        return redirect(url_for("prompt_detail", name=name))

    return app


# ------------------------------------------------------------------ #
#  Auxiliares                                                         #
# ------------------------------------------------------------------ #


def _validate_prompt_dir():
    """Verifica se o diretório de prompts existe e tem permissão de escrita."""
    from pathlib import Path

    path = Path(settings.prompt_dir)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise RuntimeError(f"PROMPT_DIR '{settings.prompt_dir}' não é um diretório.")
    test_file = path / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
    except OSError:
        raise RuntimeError(
            f"PROMPT_DIR '{settings.prompt_dir}' não tem permissão de escrita."
        )


def _parse_optional_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
