"""Piezas de tipo ``tool`` (RFC-002 §4.3), con un ejecutor simulado: nunca se ejecuta nada real."""

import shutil

import pytest

from cuypilot.catalog import CATALOG_DIR, load_catalog
from cuypilot.workspace import INSTRUCTIONS_PATH, CuypilotError, Workspace

FAKE_TOOL = """
[items.faketool]
type = "tool"
version = "1.2.3"
description = "Herramienta de prueba."
license = "MIT"
install = [["uv", "tool", "install", "faketool==1.2.3"]]
configure = [["faketool", "vscode", "install"]]
uninstall = [["faketool", "vscode", "uninstall"]]
check = ["faketool", "--version"]
gitignore = ["faketool-out/"]
instructions = "- Use `faketool --safe`."
"""


class FakeShell:
    """Simula comandos: registra lo que se ejecuta y responde ``check`` con la versión instalada."""

    def __init__(self, installed: str | None = None, fail: str | None = None):
        self.installed = installed
        self.fail = fail
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, cmd, cwd):
        if cmd[1:] == ("--version",):
            return (0, f"faketool {self.installed}") if self.installed else (127, "not found")
        self.calls.append(cmd)
        if self.fail and self.fail in cmd:
            return 1, "boom"
        if cmd[:3] == ("uv", "tool", "install"):
            self.installed = cmd[-1].split("==")[1]
        return 0, ""


@pytest.fixture
def catalog_dir(tmp_path):
    dest = tmp_path / "catalog"
    shutil.copytree(CATALOG_DIR, dest)
    (dest / "catalog.toml").write_text((dest / "catalog.toml").read_text() + FAKE_TOOL)
    return dest


def ws(root, catalog_dir, shell, answer=True, asked=None):
    def confirm(commands):
        if asked is not None:
            asked.extend(commands)
        return answer

    return Workspace(root, load_catalog(catalog_dir), "0.0.0-test", catalog_dir, run=shell, confirm=confirm)


def test_add_tool_confirms_runs_and_records(tmp_path, catalog_dir):
    project, shell, asked = tmp_path / "p", FakeShell(), []
    project.mkdir()

    ws(project, catalog_dir, shell, asked=asked).add(["faketool"])

    expected = [("uv", "tool", "install", "faketool==1.2.3"), ("faketool", "vscode", "install")]
    assert asked == expected and shell.calls == expected
    assert "faketool-out/" in (project / ".gitignore").read_text().splitlines()
    assert "Use `faketool --safe`" in (project / INSTRUCTIONS_PATH).read_text()
    assert ws(project, catalog_dir, shell).status() == {"faketool": "ok"}


def test_add_tool_skips_install_when_version_matches(tmp_path, catalog_dir):
    shell = FakeShell(installed="1.2.3")
    ws(tmp_path, catalog_dir, shell).add(["faketool"])
    assert shell.calls == [("faketool", "vscode", "install")]


def test_cancel_changes_nothing(tmp_path, catalog_dir):
    shell = FakeShell()
    with pytest.raises(CuypilotError, match="Cancelado"):
        ws(tmp_path, catalog_dir, shell, answer=False).add(["faketool", "python-design"])
    assert shell.calls == []
    assert not (tmp_path / ".github").exists()


def test_failed_command_stops_and_records_nothing(tmp_path, catalog_dir):
    shell = FakeShell(fail="vscode")
    with pytest.raises(CuypilotError, match="boom"):
        ws(tmp_path, catalog_dir, shell).add(["faketool"])
    assert ws(tmp_path, catalog_dir, shell).status() == {}


def test_plan_add_is_side_effect_free(tmp_path, catalog_dir):
    project, shell = tmp_path / "p", FakeShell()
    project.mkdir()
    items, commands = ws(project, catalog_dir, shell).plan_add(["faketool"])
    assert [i.name for i in items] == ["faketool"] and len(commands) == 2
    assert shell.calls == [] and not any(project.iterdir())


def test_status_and_update_detect_version_drift(tmp_path, catalog_dir):
    shell = FakeShell()
    ws(tmp_path, catalog_dir, shell).add(["faketool"])
    shell.installed = "1.0.0"
    assert ws(tmp_path, catalog_dir, shell).status() == {"faketool": "desactualizada"}

    ws(tmp_path, catalog_dir, shell).update()
    assert shell.installed == "1.2.3"
    assert ws(tmp_path, catalog_dir, shell).status() == {"faketool": "ok"}

    shell.installed = None
    assert ws(tmp_path, catalog_dir, shell).status() == {"faketool": "no instalada"}


def test_remove_tool_runs_uninstall_and_cleans_block(tmp_path, catalog_dir):
    shell = FakeShell()
    ws(tmp_path, catalog_dir, shell).add(["faketool", "python-design"])
    report = ws(tmp_path, catalog_dir, shell).remove(["faketool"])

    assert shell.calls[-1] == ("faketool", "vscode", "uninstall")
    assert "sigue instalado" in report.notes[0]
    assert "faketool --safe" not in (tmp_path / INSTRUCTIONS_PATH).read_text()
