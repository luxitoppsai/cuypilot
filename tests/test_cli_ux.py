"""Contratos de lectura en terminal estrecha y automatización; sin snapshots estéticos."""

import argparse
import io
from dataclasses import replace

import pytest

from cuypilot.catalog import load_catalog
from cuypilot.cli import _cmd_list, _cmd_status, _print_report, main
from cuypilot.console import paint
from cuypilot.wizard import banner
from cuypilot.workspace import Report, Workspace


def test_version_is_one_plain_line(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    output = capsys.readouterr().out
    assert output.startswith("cuypilot ") and len(output.splitlines()) == 1
    assert "\033[" not in output


@pytest.mark.parametrize("width", [48, 80])
def test_catalog_fits_terminal_and_keeps_commands_copyable(tmp_path, monkeypatch, capsys, width):
    monkeypatch.setenv("COLUMNS", str(width))
    ws = Workspace(tmp_path, load_catalog(), "0.6.0")
    ws.add(["docs-writer"])
    _cmd_list(ws, argparse.Namespace(type="agent"))
    output = capsys.readouterr().out
    assert all(len(line) <= width for line in output.splitlines())
    assert "* docs-writer" in output
    assert "cuypilot list --type skill" in output.splitlines()[-1]
    assert "\033[" not in output


def test_status_prioritizes_edits_and_does_not_recommend_force(tmp_path, capsys):
    ws = Workspace(tmp_path, load_catalog(), "0.6.0")
    ws.add(["docs-writer", "python-design"])
    path = tmp_path / next(iter(ws.lock["python-design"]["files"]))
    path.write_text("local edit")
    ws.catalog["docs-writer"] = replace(ws.catalog["docs-writer"], version="2.0.0")
    _cmd_status(ws, argparse.Namespace())
    output = capsys.readouterr().out
    assert output.index("python-design: modificada") < output.index("docs-writer: desactualizada")
    assert "requieren atención" in output
    assert "revisa el diff" in output and "--dry-run" in output
    assert "--force" not in output


def test_skipped_local_edits_are_not_presented_as_unqualified_success(capsys):
    _print_report(
        Report(skipped={"python-design": "modificada localmente (usa --force para pisarla)"}), "actualizada"
    )
    output = capsys.readouterr().out
    assert "[!]" in output and "[OK]" not in output
    assert "se conservaron" in output


def test_outdated_empty_and_up_to_date_states_are_explicit(tmp_path, capsys):
    args = ["outdated", "--path", str(tmp_path)]
    assert main(args) == 0
    assert "No hay piezas instaladas" in capsys.readouterr().out
    Workspace(tmp_path, load_catalog(), "0.6.0").add(["python-design"])
    assert main(args) == 0
    assert "No hay actualizaciones pendientes" in capsys.readouterr().out


def test_narrow_banner_and_stream_specific_no_color(monkeypatch):
    monkeypatch.setenv("COLUMNS", "48")
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert "/____/_/" not in banner("0.6.0")
    assert "cuypilot 0.6.0" in banner("0.6.0")
    pipe, terminal = io.StringIO(), io.StringIO()
    monkeypatch.setattr(terminal, "isatty", lambda: True)
    assert paint("Error", "31", stream=pipe) == "Error"
    assert "\033[31m" in paint("Error", "31", stream=terminal)
    monkeypatch.setenv("NO_COLOR", "")
    assert paint("Error", "31", stream=terminal) == "Error"


def test_catalog_heading_is_not_duplicated(tmp_path, capsys):
    assert main(["list", "--type", "agent", "--path", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert output.count("GitHub Copilot (VS Code)") == 1
