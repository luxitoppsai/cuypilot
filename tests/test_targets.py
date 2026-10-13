"""Contratos de instalación y versiones al convivir varios asistentes."""

import json
from dataclasses import replace

import pytest

from cuypilot.catalog import CATALOG_DIR, load_catalog, load_roles
from cuypilot.cli import main
from cuypilot.targets import TARGETS
from cuypilot.wizard import run_wizard
from cuypilot.workspace import CuypilotError, Workspace


def workspace(path, target):
    return Workspace(path, load_catalog(), "0.5.0", target=target)


def test_three_targets_coexist_and_remove_preserves_other_blocks(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# Project\nUser conventions.\n")
    for target in TARGETS:
        workspace(tmp_path, target).add(["python-standards", "docs-writer"])
    assert (tmp_path / ".github/skills/sphinx-docstrings/SKILL.md").exists()
    assert (tmp_path / ".opencode/agents/docs-writer.md").exists()
    assert (tmp_path / ".assistant/skills/docs-writer/SKILL.md").exists()
    for target in TARGETS:
        assert set(workspace(tmp_path, target).status().values()) == {"ok"}
    genie_lock = (tmp_path / ".assistant/cuypilot.lock.json").read_bytes()
    workspace(tmp_path, "opencode").remove(["python-standards", "docs-writer", "sphinx-docstrings"])
    assert (tmp_path / "AGENTS.md").read_text().startswith("# Project\nUser conventions.")
    assert "cuypilot:genie:start" in (tmp_path / "AGENTS.md").read_text()
    assert "cuypilot:opencode:start" not in (tmp_path / "AGENTS.md").read_text()
    assert (tmp_path / ".assistant/cuypilot.lock.json").read_bytes() == genie_lock
    assert set(workspace(tmp_path, "genie").status().values()) == {"ok"}
    assert set(workspace(tmp_path, "copilot").status().values()) == {"ok"}


@pytest.mark.parametrize("target", ["opencode", "genie"])
def test_scripts_use_target_paths_and_manual_skill_remains_explicit(tmp_path, target):
    ws = workspace(tmp_path, target)
    ws.add(["improve-prompt", "sphinx-docstrings", "python-standards"])
    text = (tmp_path / f"{ws.target.directory}/skills/improve-prompt/SKILL.md").read_text()
    assert ".github/" not in text
    assert f"{ws.target.directory}/skills/improve-prompt/scripts/workspace_context.py" in text
    assert "only when the user explicitly requests" in text
    assert "disable-model-invocation:" not in text
    assert "Apply the following rules" in (tmp_path / "AGENTS.md").read_text()
    assert "**/*.py" in (tmp_path / "AGENTS.md").read_text()
    assert (tmp_path / f"{ws.target.directory}/skills/improve-prompt/scripts/workspace_context.py").exists()


@pytest.mark.parametrize("target", ["opencode", "genie"])
def test_agent_rendering_preserves_original_type_and_dependencies(tmp_path, target):
    ws = workspace(tmp_path, target)
    ws.add(["docs-writer", "spark-performance"])
    if target == "genie":
        text = (tmp_path / ".assistant/skills/docs-writer/SKILL.md").read_text()
        assert "name: docs-writer" in text and "adapted as a Genie Code skill" in text
    else:
        text = (tmp_path / ".opencode/agents/docs-writer.md").read_text()
        assert "mode: all" in text and "description:" in text
        assert "name:" not in text.split("---")[1]
    fresh = workspace(tmp_path, target)
    assert fresh.lock["docs-writer"]["type"] == "agent"
    assert fresh.lock["docs-writer"]["requires"] == ["sphinx-docstrings"]
    with pytest.raises(CuypilotError, match="docs-writer"):
        fresh.remove(["sphinx-docstrings"])


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("name", ["python-design", "docs-writer", "python-standards"])
def test_version_only_change_is_outdated(tmp_path, target, name):
    ws = workspace(tmp_path, target)
    ws.add([name])
    ws.catalog[name] = replace(ws.catalog[name], version="2.0.0")
    assert ws.status()[name] == "desactualizada"
    ws.update()
    assert ws.lock[name]["version"] == "2.0.0"
    assert ws.status()[name] == "ok"


def test_recorded_dependencies_win_over_new_catalog(tmp_path):
    ws = workspace(tmp_path, "genie")
    ws.add(["docs-writer"])
    ws.catalog["docs-writer"] = replace(ws.catalog["docs-writer"], requires=())
    with pytest.raises(CuypilotError, match="docs-writer"):
        ws.remove(["sphinx-docstrings"])


def test_dependency_only_change_is_outdated_and_installed(tmp_path):
    ws = workspace(tmp_path, "genie")
    ws.add(["python-design"])
    ws.catalog["python-design"] = replace(ws.catalog["python-design"], requires=("sphinx-docstrings",))
    assert ws.status()["python-design"] == "desactualizada"
    ws.update()
    assert "sphinx-docstrings" in ws.lock
    assert ws.lock["python-design"]["requires"] == ["sphinx-docstrings"]


@pytest.mark.parametrize("target,tool", [("genie", "graphify"), ("genie", "pyspark-antipattern")])
def test_incompatible_tools_abort_without_effects(tmp_path, target, tool):
    calls = []
    ws = Workspace(tmp_path, load_catalog(), "0.5.0", target=target, run=lambda *args: calls.append(args))
    with pytest.raises(CuypilotError, match="No compatible"):
        ws.add(["python-design", tool])
    assert not calls and not list(tmp_path.iterdir())


@pytest.mark.parametrize("target", TARGETS)
def test_other_destination_cannot_be_claimed_by_lock(tmp_path, target):
    ws = workspace(tmp_path, target)
    ws.add(["python-design"])
    path = tmp_path / ws.lock_path
    payload = json.loads(path.read_text())
    payload["items"]["python-design"]["files"] = {
        ".other/skills/python-design/SKILL.md": "sha256:" + "0" * 64
    }
    path.write_text(json.dumps(payload))
    with pytest.raises(CuypilotError, match="Lockfile inválido"):
        workspace(tmp_path, target)


@pytest.mark.parametrize("target", TARGETS)
def test_managed_instruction_edits_are_protected(tmp_path, target):
    ws = workspace(tmp_path, target)
    ws.add(["python-standards"])
    path = tmp_path / ws.instructions_path
    path.write_text(path.read_text().replace("simplest", "most complicated"))
    ws = workspace(tmp_path, target)
    assert ws.status()["python-standards"] == "modificada"
    with pytest.raises(CuypilotError, match="Bloque gestionado modificado"):
        ws.update()
    ws.update(force=True)
    assert ws.status()["python-standards"] == "ok"


def test_legacy_copilot_lock_still_works(tmp_path):
    ws = workspace(tmp_path, "copilot")
    ws.add(["python-design"])
    path = tmp_path / ws.lock_path
    payload = json.loads(path.read_text())
    payload.pop("target")
    payload.pop("managed_hash")
    payload["items"]["python-design"].pop("requires")
    path.write_text(json.dumps(payload))
    assert workspace(tmp_path, "copilot").status() == {"python-design": "ok"}


def test_target_and_path_options_before_or_after_command(tmp_path, capsys):
    assert main(["--target", "opencode", "add", "python-design", "--path", str(tmp_path)]) == 0
    assert main(["status", "--target", "opencode", "--path", str(tmp_path)]) == 0
    assert "instalada 1.0.0" in capsys.readouterr().out
    assert not (tmp_path / ".github").exists()


def test_genie_wizard_uses_adapted_agents_without_local_tools(tmp_path, capsys):
    ws = workspace(tmp_path, "genie")
    assert run_wizard(ws, load_roles(), "0.5.0", role="docs", assume_yes=True) == 0
    assert "docs-writer" in ws.lock
    assert "registra la carpeta .assistant/skills" in capsys.readouterr().out
    assert not any(entry["type"] == "tool" for entry in ws.lock.values())


def test_catalog_compatibility_is_declared():
    for item in load_catalog().values():
        assert item.targets and set(item.targets) <= TARGETS.keys()
        if item.type == "tool":
            assert "genie" not in item.targets
    for target in TARGETS.values():
        for item in load_catalog().values():
            if target.supports(item):
                rendered = target.render(item, CATALOG_DIR)
                assert all(target.owns(item.name, item.type, path) for path in rendered)


def test_failed_update_restores_shared_agents_and_other_destination(tmp_path, monkeypatch):
    opencode = workspace(tmp_path, "opencode")
    genie = workspace(tmp_path, "genie")
    opencode.add(["python-standards"])
    genie.add(["python-standards"])
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    opencode.catalog["python-standards"] = replace(opencode.catalog["python-standards"], version="2.0.0")
    save = opencode._save

    def fail_after_save():
        save()
        raise OSError("simulated failure")

    monkeypatch.setattr(opencode, "_save", fail_after_save)
    with pytest.raises(OSError, match="simulated failure"):
        opencode.update()
    assert before == {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert workspace(tmp_path, "genie").status() == {"python-standards": "ok"}
