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
