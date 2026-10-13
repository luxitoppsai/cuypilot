"""Comportamiento de la CLI sobre un workspace temporal (criterios de aceptación de RFC-001 §9)."""

import json
import shutil
from pathlib import Path

import pytest

from cuypilot.catalog import CATALOG_DIR, load_catalog
from cuypilot.cli import main
from cuypilot.workspace import INSTRUCTIONS_PATH, LOCK_PATH, START, CuypilotError, Workspace

SKILL = ".github/skills/sphinx-docstrings/SKILL.md"


def ws(root: Path, catalog_dir: Path = CATALOG_DIR) -> Workspace:
    """Workspace recién leído de disco, como en cada invocación de la CLI."""
    return Workspace(root, load_catalog(catalog_dir), "0.0.0-test", catalog_dir)


def test_add_installs_item_lock_and_base_block(tmp_path):
    report = ws(tmp_path).add(["sphinx-docstrings"])

    assert report.done == ["sphinx-docstrings"]
    assert (tmp_path / SKILL).read_bytes() == (CATALOG_DIR / "skills/sphinx-docstrings/SKILL.md").read_bytes()
    lock = json.loads((tmp_path / LOCK_PATH).read_text())
    assert lock["items"]["sphinx-docstrings"]["version"] == load_catalog()["sphinx-docstrings"].version
    assert START in (tmp_path / INSTRUCTIONS_PATH).read_text()


def test_add_installs_requires_and_skips_installed(tmp_path):
    ws(tmp_path).add(["sphinx-docstrings"])
    report = ws(tmp_path).add(["docs-writer"])

    assert report.done == ["docs-writer"]
    assert "sphinx-docstrings" in report.skipped
    assert (tmp_path / ".github/agents/docs-writer.agent.md").is_file()


def test_add_unknown_item_fails(tmp_path):
    with pytest.raises(CuypilotError, match="No existe"):
        ws(tmp_path).add(["nope"])


def test_add_refuses_foreign_files_unless_forced(tmp_path):
    (tmp_path / SKILL).parent.mkdir(parents=True)
    (tmp_path / SKILL).write_text("mine")

    with pytest.raises(CuypilotError, match="--force"):
        ws(tmp_path).add(["sphinx-docstrings"])
    assert (tmp_path / SKILL).read_text() == "mine"

    ws(tmp_path).add(["sphinx-docstrings"], force=True)
    assert (tmp_path / SKILL).read_text() != "mine"


def test_user_content_outside_block_is_preserved(tmp_path):
    original = "# My project\n\nUse tabs.\n"
    (tmp_path / INSTRUCTIONS_PATH).parent.mkdir(parents=True)
    (tmp_path / INSTRUCTIONS_PATH).write_text(original)

    ws(tmp_path).add(["sphinx-docstrings"])
    ws(tmp_path).add(["python-standards"])
    text = (tmp_path / INSTRUCTIONS_PATH).read_text()
    assert text.startswith(original) and text.count(START) == 1

    ws(tmp_path).remove(["sphinx-docstrings", "python-standards"])
    assert (tmp_path / INSTRUCTIONS_PATH).read_text() == original


def test_remove_cleans_everything(tmp_path):
    ws(tmp_path).add(["python-design"])
    ws(tmp_path).remove(["python-design"])

    assert not (tmp_path / ".github/skills").exists()
    assert not (tmp_path / LOCK_PATH).exists()
    assert not (tmp_path / INSTRUCTIONS_PATH).exists()


def test_remove_refuses_when_dependents_installed(tmp_path):
    ws(tmp_path).add(["docs-writer"])
    with pytest.raises(CuypilotError, match="docs-writer"):
        ws(tmp_path).remove(["sphinx-docstrings"])
    ws(tmp_path).remove(["docs-writer", "sphinx-docstrings"])


@pytest.mark.parametrize("target", ["copilot", "opencode", "genie"])
def test_remove_preserves_local_edits_unless_forced(tmp_path, target):
    workspace = Workspace(tmp_path, load_catalog(), "test", target=target)
    workspace.add(["python-design"])
    path = tmp_path / next(iter(workspace.lock["python-design"]["files"]))
    path.write_text("local edit")
    with pytest.raises(CuypilotError, match="--force"):
        workspace.remove(["python-design"])
    assert path.read_text() == "local edit"
    assert "python-design" in workspace.lock
    workspace.remove(["python-design"], force=True)
    assert not path.exists()


@pytest.mark.parametrize("target", ["copilot", "opencode", "genie"])
def test_update_protects_foreign_files_added_to_existing_skill(tmp_path, target):
    catalog_dir = tmp_path / "catalog"
    shutil.copytree(CATALOG_DIR, catalog_dir)
    root = tmp_path / "project"
    workspace = Workspace(root, load_catalog(catalog_dir), "test", catalog_dir, target=target)
    workspace.add(["python-design"])
    skill_path = root / next(iter(workspace.lock["python-design"]["files"]))
    resource = skill_path.parent / "references" / "example.md"
    resource.parent.mkdir(exist_ok=True)
    resource.write_text("team notes")
    source = catalog_dir / "skills/python-design/references/example.md"
    source.parent.mkdir(exist_ok=True)
    source.write_text("new catalogue resource")
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(CuypilotError, match="Archivos ajenos"):
        workspace.update()
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    workspace.update(force=True)
    assert resource.read_text() == "new catalogue resource"


def test_status_detects_local_edits_and_update_respects_them(tmp_path):
    ws(tmp_path).add(["sphinx-docstrings"])
    assert ws(tmp_path).status() == {"sphinx-docstrings": "ok"}

    (tmp_path / SKILL).write_text("local edit")
    assert ws(tmp_path).status() == {"sphinx-docstrings": "modificada"}

    report = ws(tmp_path).update()
    assert "sphinx-docstrings" in report.skipped
    assert (tmp_path / SKILL).read_text() == "local edit"

    ws(tmp_path).update(force=True)
    assert ws(tmp_path).status() == {"sphinx-docstrings": "ok"}


@pytest.fixture
def catalog_copy(tmp_path):
    """Copia editable del catálogo, para simular una versión nueva del wheel."""
    dest = tmp_path / "catalog"
    shutil.copytree(CATALOG_DIR, dest)
    return dest


def test_update_applies_new_catalog_content(tmp_path, catalog_copy):
    project = tmp_path / "project"
    ws(project, catalog_copy).add(["python-design"])

    skill = catalog_copy / "skills/python-design/SKILL.md"
    skill.write_text(skill.read_text() + "\nNew rule.\n")
    (catalog_copy / "skills/python-design/references/patterns.md").unlink()
    assert ws(project, catalog_copy).status() == {"python-design": "desactualizada"}

    assert ws(project, catalog_copy).update().done == ["python-design"]
    assert (project / ".github/skills/python-design/SKILL.md").read_text().endswith("New rule.\n")
    assert not (project / ".github/skills/python-design/references").exists()
    assert ws(project, catalog_copy).status() == {"python-design": "ok"}


def test_retired_item_is_reported(tmp_path, catalog_copy):
    project = tmp_path / "project"
    ws(project, catalog_copy).add(["python-design"])
    toml = catalog_copy / "catalog.toml"
    toml.write_text(toml.read_text().replace("[items.python-design]", "[items.renamed-design]"))

    assert ws(project, catalog_copy).status() == {"python-design": "retirada"}
    assert "python-design" in ws(project, catalog_copy).update().skipped


def test_cli_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["add", "docs-writer"]) == 0
    assert main(["status"]) == 0
    assert "docs-writer: ok" in capsys.readouterr().out
    assert main(["list", "--type", "agent"]) == 0
    assert "* docs-writer" in capsys.readouterr().out
    assert main(["remove", "nope"]) == 1


def _strip_h2_section(text: str, heading: str) -> str:
    """Reproduce cómo graphify quita su sección: desde ``heading`` hasta el siguiente ``## `` o EOF."""
    lines = text.split("\n")
    start = lines.index(heading)
    end = next((j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
    return "\n".join(lines[:start] + lines[end:])


def test_block_survives_other_tools_h2_sections(tmp_path):
    path = tmp_path / INSTRUCTIONS_PATH
    path.parent.mkdir(parents=True)
    path.write_text("## graphify\n\nUse graphify query.\n")

    ws(tmp_path).add(["python-design"])  # el bloque queda DESPUÉS de la sección ajena
    path.write_text(_strip_h2_section(path.read_text(), "## graphify"))
    assert START in path.read_text()

    ws(tmp_path).remove(["python-design"])
    assert not path.exists() or START not in path.read_text()


def test_v010_block_format_is_migrated(tmp_path):
    path = tmp_path / INSTRUCTIONS_PATH
    path.parent.mkdir(parents=True)
    path.write_text("# Mine\n\n<!-- cuypilot:start -->\n## Team conventions\nold\n<!-- cuypilot:end -->\n")
    ws(tmp_path).add(["python-design"])
    text = path.read_text()
    assert text.count(START) == 1 and "old" not in text
    assert text.startswith("# Mine\n\n## Team conventions (managed by cuypilot")


def test_bytecode_caches_are_never_copied(tmp_path):
    """pip compila bytecode al instalar el wheel: los __pycache__ del catálogo no deben llegar al repo."""
    catalog = tmp_path / "catalog"
    shutil.copytree(CATALOG_DIR, catalog)
    cache = catalog / "skills/sphinx-docstrings/scripts/__pycache__"
    cache.mkdir(exist_ok=True)
    (cache / "docstring_audit.cpython-311.pyc").write_bytes(b"\x00")

    project = tmp_path / "project"
    ws(project, catalog).add(["sphinx-docstrings"])
    assert not list(project.rglob("__pycache__"))


@pytest.mark.parametrize("payload", [None, {}, {"cuypilot_version": "1", "items": []}])
def test_invalid_lock_is_rejected(tmp_path, payload):
    target = tmp_path / LOCK_PATH
    target.parent.mkdir()
    target.write_text(json.dumps(payload))
    with pytest.raises(CuypilotError, match="Lockfile inválido"):
        ws(tmp_path)


@pytest.mark.parametrize(
    "relative", ["../victim", "/tmp/victim", ".github/skills/python-design/../../victim"]
)
def test_lock_cannot_claim_external_files(tmp_path, relative):
    ws(tmp_path).add(["python-design"])
    target = tmp_path / LOCK_PATH
    payload = json.loads(target.read_text())
    payload["items"]["python-design"]["files"] = {relative: "sha256:" + "0" * 64}
    target.write_text(json.dumps(payload))
    with pytest.raises(CuypilotError, match="Ruta no permitida"):
        ws(tmp_path)


def test_symlink_destination_is_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    (project / ".github").symlink_to(outside, target_is_directory=True)
    with pytest.raises(CuypilotError, match="Enlace simbólico"):
        ws(project)
    assert not list(outside.iterdir())


def test_update_checks_foreign_new_dependency(tmp_path, catalog_copy):
    from dataclasses import replace

    project = tmp_path / "project"
    workspace = ws(project, catalog_copy)
    workspace.add(["python-design"])
    skill = catalog_copy / "skills/python-design/SKILL.md"
    skill.write_text(skill.read_text() + "\nNew rule.\n")
    workspace.catalog["python-design"] = replace(
        workspace.catalog["python-design"], requires=("sphinx-docstrings",)
    )
    foreign = project / SKILL
    foreign.parent.mkdir(parents=True)
    foreign.write_text("mine")
    before = (project / LOCK_PATH).read_bytes()
    with pytest.raises(CuypilotError, match="dependencias nuevas"):
        workspace.update()
    assert foreign.read_text() == "mine"
    assert (project / LOCK_PATH).read_bytes() == before


def test_failed_save_restores_files_and_lock(tmp_path, monkeypatch):
    workspace = ws(tmp_path)
    workspace.add(["python-design"])
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    original_save = workspace._save

    def fail_after_save():
        original_save()
        raise OSError("disk failure")

    monkeypatch.setattr(workspace, "_save", fail_after_save)
    with pytest.raises(OSError, match="disk failure"):
        workspace.add(["sphinx-docstrings"])
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before
    assert set(workspace.lock) == {"python-design"}


def test_cli_invalid_json_has_no_traceback(tmp_path, monkeypatch, capsys):
    target = tmp_path / LOCK_PATH
    target.parent.mkdir()
    target.write_text("{")
    monkeypatch.chdir(tmp_path)
    assert main(["status"]) == 1
    assert "Lockfile inválido" in capsys.readouterr().err


def test_broken_managed_block_changes_nothing(tmp_path):
    target = tmp_path / INSTRUCTIONS_PATH
    target.parent.mkdir()
    target.write_text(START + "\nuser content")
    with pytest.raises(CuypilotError, match="Bloque gestionado inválido"):
        ws(tmp_path).add(["python-design"])
    assert target.read_text() == START + "\nuser content"


@pytest.mark.parametrize("operation", ["update", "remove"])
def test_failed_operation_restores_existing_files(tmp_path, monkeypatch, operation):
    workspace = ws(tmp_path)
    workspace.add(["python-design"])
    if operation == "update":
        (tmp_path / ".github/skills/python-design/SKILL.md").write_text("local edit")
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def fail_save():
        raise OSError("save failure")

    monkeypatch.setattr(workspace, "_save", fail_save)
    with pytest.raises(OSError, match="save failure"):
        if operation == "update":
            workspace.update(force=True)
        else:
            workspace.remove(["python-design"])
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after
    assert set(workspace.lock) == {"python-design"}


def test_force_cannot_follow_skill_symlink(tmp_path):
    workspace = ws(tmp_path)
    target = tmp_path / ".github/skills/python-design"
    target.parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    target.symlink_to(outside, target_is_directory=True)
    with pytest.raises(CuypilotError, match="Enlace simbólico"):
        workspace.add(["python-design"], force=True)
    assert not list(outside.iterdir())


def test_parent_file_is_rejected_before_tool_commands(tmp_path):
    workspace = Workspace(tmp_path, load_catalog(), "test", run=lambda *args: pytest.fail("command ran"))
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github/skills").write_text("mine")
    with pytest.raises(CuypilotError, match="Directorio inválido"):
        workspace.add(["python-design", "graphify"])
    assert (tmp_path / ".github/skills").read_text() == "mine"
