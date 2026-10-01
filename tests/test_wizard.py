"""Wizard `cuypilot init` (RFC-003 §4.8)."""

from cuypilot.catalog import load_catalog, load_roles
from cuypilot.cli import main
from cuypilot.wizard import run_wizard
from cuypilot.workspace import Workspace


def answers(*replies):
    it = iter(replies)
    return lambda prompt: next(it)


def wizard(tmp_path, *replies, **kwargs):
    ws = Workspace(tmp_path, load_catalog(), "0.0.0-test")
    code = run_wizard(ws, load_roles(), "0.0.0-test", ask=answers(*replies), **kwargs)
    return code, Workspace(tmp_path, load_catalog(), "0.0.0-test")


def test_role_installs_suggested_pieces_without_tools(tmp_path, capsys):
    roles = load_roles()
    mle = list(roles).index("mle") + 1
    # rol, graphify? no, pyspark-antipattern? no, ¿instalar? (Enter = sí)
    code, ws = wizard(tmp_path, str(mle), "n", "n", "")
    out = capsys.readouterr().out

    assert code == 0
    assert set(roles["mle"]["items"]) <= set(ws.lock)
    assert "graphify" not in ws.lock
    assert "/____/_/" in out and "\033[" not in out  # banner, sin colores fuera de una terminal


def test_manual_selection_and_invalid_answer(tmp_path, capsys):
    manual = len(load_roles()) + 1
    code, ws = wizard(tmp_path, "99", str(manual), "1, 2", "n", "n", "s")
    assert code == 0 and len(ws.lock) >= 2
    assert "Escribe un número" in capsys.readouterr().out


def test_cancel_installs_nothing(tmp_path):
    code, ws = wizard(tmp_path, "1", "n", "n", "n")
    assert code == 0 and ws.lock == {}
    assert not (tmp_path / ".github").exists()


def test_non_interactive_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--role", "docs", "--yes"]) == 0
    lock = Workspace(tmp_path, load_catalog(), "x").lock
    assert set(load_roles()["docs"]["items"]) <= set(lock)

    assert main(["init", "--yes"]) == 1  # --yes sin --role
    assert main([]) == 0  # sin argumentos y con piezas instaladas: muestra la ayuda
    assert "usage: cuypilot" in capsys.readouterr().out


def test_no_args_on_fresh_repo_opens_wizard(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    replies = iter(["1", "n", "n", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(replies))
    assert main([]) == 0
    assert "¿Cuál es tu rol?" in capsys.readouterr().out
