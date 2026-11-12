"""RFC-008: intención, validación frozen, consultas y rollback entre destinos."""

import json
from dataclasses import replace
from importlib.metadata import version

import pytest

from cuypilot.catalog import load_catalog
from cuypilot.cli import main
from cuypilot.manifest import Manifest, check_version
from cuypilot.project import Project
from cuypilot.targets import TARGETS
from cuypilot.workspace import CuypilotError, Workspace


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def project(root, targets=("copilot",), pieces=("docs-writer",)):
    manifest = Manifest(">=0.6,<0.7", targets, pieces)
    manifest.write(root / "cuypilot.toml")
    return Project(Workspace(root, load_catalog(), "0.6.0"))


@pytest.mark.parametrize("target", TARGETS)
def test_install_expands_dependencies_and_frozen_is_read_only(tmp_path, target):
    p = project(tmp_path, (target,))
    p.install()
    before = snapshot(tmp_path)
    assert p.differences(frozen=True) == []
    assert snapshot(tmp_path) == before
    assert set(p.workspaces[target].lock) == {"docs-writer", "sphinx-docstrings"}


@pytest.mark.parametrize("change", ["edit", "delete", "add", "block", "lock", "manifest"])
def test_frozen_rejects_drift_without_mutation(tmp_path, change):
    p = project(tmp_path)
    p.install()
    ws = p.workspaces["copilot"]
    skill = tmp_path / ".github/skills/sphinx-docstrings/SKILL.md"
    if change == "edit":
        skill.write_text("edited")
    elif change == "delete":
        skill.unlink()
    elif change == "add":
        (skill.parent / "unexpected.md").write_text("extra")
    elif change == "block":
        path = tmp_path / ws.instructions_path
        path.write_text(path.read_text().replace("simplest", "complex"))
    elif change == "lock":
        path = tmp_path / ws.lock_path
        payload = json.loads(path.read_text())
        del payload["items"]["docs-writer"]
        path.write_text(json.dumps(payload))
    else:
        Manifest(">=0.6,<0.7", ("copilot",), ("python-design",)).write(p.path)
    before = snapshot(tmp_path)
    assert main(["install", "--frozen", "--path", str(tmp_path)]) == 1
    assert snapshot(tmp_path) == before


def test_add_remove_update_manifest_and_all_destinations(tmp_path):
    p = project(tmp_path, tuple(TARGETS))
    p.install()
    p.change(["python-design"])
    assert "python-design" in Manifest.read(p.path, "0.6.0").pieces
    assert all("python-design" in ws.lock for ws in p.workspaces.values())
    p.change(["python-design"], remove=True)
    assert "python-design" not in Manifest.read(p.path, "0.6.0").pieces
    assert all("python-design" not in ws.lock for ws in p.workspaces.values())
    assert p.differences(frozen=True) == []


@pytest.mark.parametrize("failure", ["second_target", "manifest"])
def test_failure_restores_manifest_and_every_target(tmp_path, monkeypatch, failure):
    p = project(tmp_path, ("opencode", "genie"))
    p.install()
    before = snapshot(tmp_path)
    locks = {target: dict(ws.lock) for target, ws in p.workspaces.items()}
    if failure == "second_target":
        original = p.workspaces["genie"]._save

        def fail():
            original()
            raise OSError("disk failure")

        monkeypatch.setattr(p.workspaces["genie"], "_save", fail)
    else:
        original = Manifest.write

        def fail(self, path):
            original(self, path)
            raise OSError("disk failure")

        monkeypatch.setattr(Manifest, "write", fail)
    with pytest.raises(OSError, match="disk failure"):
        p.change(["python-design"])
    assert snapshot(tmp_path) == before
    assert all(ws.lock == locks[target] for target, ws in p.workspaces.items())


@pytest.mark.parametrize("requirement", [">=9", ">=0.6,<0.6", "~=0.6", "*", "", ">=0.6,garbage"])
def test_bad_or_incompatible_range_changes_nothing(tmp_path, requirement):
    Manifest(requirement, ("copilot",), ("python-design",)).write(tmp_path / "cuypilot.toml")
    before = snapshot(tmp_path)
    assert main(["install", "--path", str(tmp_path)]) == 1
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("requirement", [">=0.6,<0.7", "==0.6.0", "!=0.5,<=0.6", ">0.5,<1"])
def test_supported_ranges(requirement):
    check_version(requirement, "0.6.0")


@pytest.mark.parametrize(
    "text",
    [
        'cuypilot = ">=0.6"\npieces = "docs-writer"',
        'cuypilot = ">=0.6"\npieces = ["../escape"]',
        'cuypilot = ">=0.6"\ntargets = ["unknown"]',
        'cuypilot = ">=0.6"\ntargets = []',
        'cuypilot = ">=0.6"\npieces = ["a", "a"]',
        'cuypilot = ">=0.6"\nextra = 1',
        'cuypilot = ">=0.6"\npieces = ["a"]\ntools = ["a"]',
        'pieces = ["docs-writer"]',
        "not toml",
    ],
)
def test_schema_rejects_external_input(tmp_path, text):
    path = tmp_path / "cuypilot.toml"
    path.write_text(text)
    with pytest.raises(CuypilotError):
        Manifest.read(path, "0.6.0")


@pytest.mark.parametrize("pieces,tools", [(("unknown",), ()), (("graphify",), ()), ((), ("docs-writer",))])
def test_catalog_types_validated_before_writes(tmp_path, pieces, tools):
    Manifest(">=0.6", ("copilot",), pieces, tools).write(tmp_path / "cuypilot.toml")
    before = snapshot(tmp_path)
    assert main(["install", "--path", str(tmp_path)]) == 1
    assert snapshot(tmp_path) == before


def test_incompatible_tool_fails_before_any_destination_changes(tmp_path):
    Manifest(">=0.6", ("copilot", "genie"), (), ("graphify",)).write(tmp_path / "cuypilot.toml")
    before = snapshot(tmp_path)
    assert main(["install", "--yes", "--path", str(tmp_path)]) == 1
    assert snapshot(tmp_path) == before


def test_migration_and_detection_preserve_historical_commands(tmp_path):
    assert main(["add", "docs-writer", "--target", "opencode", "--path", str(tmp_path)]) == 0
    assert not (tmp_path / "cuypilot.toml").exists()
    before = snapshot(tmp_path)
    assert main(["install", "--frozen", "--path", str(tmp_path)]) == 1
    assert snapshot(tmp_path) == before
    assert main(["install", "--path", str(tmp_path)]) == 0
    manifest = Manifest.read(tmp_path / "cuypilot.toml", version("cuypilot"))
    assert manifest.targets == ("opencode",)
    assert main(["install", "--frozen", "--path", str(tmp_path)]) == 0


def test_different_existing_destinations_require_explicit_migration(tmp_path):
    Workspace(tmp_path, load_catalog(), "0.5.1", target="copilot").add(["python-design"])
    Workspace(tmp_path, load_catalog(), "0.5.1", target="genie").add(["docs-writer"])
    before = snapshot(tmp_path)
    assert main(["install", "--path", str(tmp_path)]) == 1
    assert snapshot(tmp_path) == before


def test_install_preserves_local_edits_and_foreign_content(tmp_path):
    p = project(tmp_path)
    p.install()
    skill = tmp_path / ".github/skills/sphinx-docstrings/SKILL.md"
    skill.write_text("local edit")
    before = snapshot(tmp_path)
    with pytest.raises(CuypilotError, match="modificada"):
        p.install()
    assert snapshot(tmp_path) == before
    p.install(force=True)
    assert p.differences(frozen=True) == []
    foreign = tmp_path / "other.txt"
    foreign.write_text("keep")
    p.change(["docs-writer"], remove=True)
    assert foreign.read_text() == "keep" and not p.workspaces["copilot"].lock


def test_queries_do_not_mutate_and_why_uses_recorded_dependencies(tmp_path, capsys):
    p = project(tmp_path)
    p.install()
    before = snapshot(tmp_path)
    for args in (["why", "sphinx-docstrings"], ["outdated"], ["update", "--dry-run"], ["audit", "--ci"]):
        assert main([*args, "--path", str(tmp_path)]) == 0
    assert "docs-writer -> sphinx-docstrings" in capsys.readouterr().out
    assert snapshot(tmp_path) == before
    ws = p.workspaces["copilot"]
    ws.catalog["docs-writer"] = replace(ws.catalog["docs-writer"], requires=())
    assert "sphinx-docstrings" in ws.lock["docs-writer"]["requires"]


def test_frozen_never_runs_tools(tmp_path):
    p = project(tmp_path, pieces=("python-design",))
    p.install()
    ws = p.workspaces["copilot"]
    tool = ws.catalog["pyspark-antipattern"]
    ws.lock[tool.name] = {
        "type": "tool",
        "version": tool.version,
        "files": {},
        "requires": [],
        "integration_hash": ws._integration_digest(tool),
    }
    ws._save()
    p.manifest = replace(p.manifest, tools=(tool.name,))

    def forbidden(*args):
        raise AssertionError("Frozen no debe ejecutar procesos")

    ws.run = forbidden
    assert not p.differences(frozen=True)


def test_explicit_target_cannot_silently_bypass_manifest(tmp_path):
    p = project(tmp_path, ("genie",))
    before = snapshot(tmp_path)
    with pytest.raises(CuypilotError, match="no figura"):
        Project(p.ws, "copilot")
    assert snapshot(tmp_path) == before


def test_init_and_install_produce_identical_files(tmp_path):
    first, second = tmp_path / "wizard", tmp_path / "declarative"
    first.mkdir()
    second.mkdir()
    assert main(["init", "--role", "docs", "--yes", "--target", "genie", "--path", str(first)]) == 0
    (second / "cuypilot.toml").write_bytes((first / "cuypilot.toml").read_bytes())
    assert main(["install", "--path", str(second)]) == 0
    assert snapshot(first) == snapshot(second)


def test_remove_required_explicit_piece_fails_without_changes(tmp_path):
    p = project(tmp_path, pieces=("docs-writer", "sphinx-docstrings"))
    p.install()
    before = snapshot(tmp_path)
    with pytest.raises(CuypilotError, match="dependen"):
        p.change(["sphinx-docstrings"], remove=True)
    assert snapshot(tmp_path) == before


def test_manifest_and_skill_symlinks_are_rejected(tmp_path):
    p = project(tmp_path)
    p.install()
    foreign = tmp_path / "foreign"
    foreign.write_text("preserve")
    link = tmp_path / ".github/skills/sphinx-docstrings/link.md"
    link.symlink_to(foreign)
    with pytest.raises(CuypilotError, match="simbólico"):
        p.differences(frozen=True)
    link.unlink()
    p.path.unlink()
    p.path.symlink_to(foreign)
    with pytest.raises(CuypilotError, match="simbólico"):
        Project(p.ws)


def test_audit_rejects_duplicate_markers_and_orphan_block(tmp_path):
    p = project(tmp_path)
    p.install()
    ws = p.workspaces["copilot"]
    path = tmp_path / ws.instructions_path
    path.write_text(path.read_text() + f"\n{ws.start}\n{ws.end}\n")
    assert any("marcadores" in line for line in p.differences())
    (tmp_path / ws.lock_path).unlink()
    p = Project(Workspace(tmp_path, load_catalog(), "0.6.0"))
    assert any("sin lockfile" in line for line in p.differences())


def test_multi_target_input_cancellation_rolls_back_first_target(tmp_path, monkeypatch):
    p = project(tmp_path, ("copilot", "opencode"))
    p.install()
    before = snapshot(tmp_path)

    def cancel(*args, **kwargs):
        raise EOFError("input closed")

    monkeypatch.setattr(p.workspaces["opencode"], "add", cancel)
    with pytest.raises(EOFError):
        p.change(["python-design"])
    assert snapshot(tmp_path) == before


def test_undeclared_generic_github_does_not_add_a_target(tmp_path):
    (tmp_path / ".github/instructions").mkdir(parents=True)
    (tmp_path / ".opencode").mkdir()
    p = Project(Workspace(tmp_path, load_catalog(), "0.6.0"))
    assert p.targets == ["opencode"]


def test_why_reports_transitive_recorded_dependencies(tmp_path, capsys):
    catalog = load_catalog()
    catalog["python-design"] = replace(catalog["python-design"], requires=("docs-writer",))
    Workspace(tmp_path, catalog, "0.6.0").add(["python-design"])
    assert main(["why", "sphinx-docstrings", "--path", str(tmp_path)]) == 0
    assert "python-design -> docs-writer -> sphinx-docstrings" in capsys.readouterr().out


def test_add_dry_run_does_not_write_manifest_or_files(tmp_path, capsys):
    p = project(tmp_path, ("opencode", "genie"))
    p.install()
    before = snapshot(tmp_path)
    assert main(["add", "python-design", "--dry-run", "--path", str(tmp_path)]) == 0
    assert "python-design" in capsys.readouterr().out
    assert snapshot(tmp_path) == before


def test_frozen_rejects_conflicting_mutation_options(tmp_path):
    p = project(tmp_path)
    p.install()
    before = snapshot(tmp_path)
    assert main(["install", "--frozen", "--force", "--path", str(tmp_path)]) == 1
    assert snapshot(tmp_path) == before


def test_removing_extra_piece_does_not_install_its_new_dependencies(tmp_path):
    p = project(tmp_path, pieces=("python-design",))
    p.install()
    ws = p.workspaces["copilot"]
    ws.catalog["python-design"] = replace(ws.catalog["python-design"], requires=("sphinx-docstrings",))
    p.change(["python-design"], remove=True)
    assert not ws.lock
    assert not (tmp_path / ".github/skills/sphinx-docstrings").exists()


def test_removed_target_is_reported_and_reconciled_preserving_foreign_rules(tmp_path):
    p = project(tmp_path, ("copilot", "genie"))
    p.install()
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# User rules\n\n" + agents.read_text())
    Manifest(">=0.6,<0.7", ("copilot",), ("docs-writer",)).write(p.path)
    p = Project(Workspace(tmp_path, load_catalog(), "0.6.0"))
    assert any("destino instalado no declarado" in line for line in p.differences(frozen=True))
    p.install()
    assert not (tmp_path / ".assistant/cuypilot.lock.json").exists()
    assert "cuypilot:genie" not in agents.read_text() and "User rules" in agents.read_text()
    assert p.differences(frozen=True) == []


def test_removed_target_with_local_edits_aborts_without_changing_other_targets(tmp_path):
    p = project(tmp_path, ("copilot", "genie"))
    p.install()
    path = tmp_path / next(iter(p.workspaces["genie"].lock["docs-writer"]["files"]))
    path.write_text("local edit")
    Manifest(">=0.6,<0.7", ("copilot",), ("docs-writer",)).write(p.path)
    p = Project(Workspace(tmp_path, load_catalog(), "0.6.0"))
    before = snapshot(tmp_path)
    with pytest.raises(CuypilotError, match="modificada"):
        p.install()
    assert snapshot(tmp_path) == before
