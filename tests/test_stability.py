"""Regresiones de integridad y planes del informe del 2026-11-12."""

import copy
import shutil

import pytest

from cuypilot.catalog import CATALOG_DIR, load_catalog
from cuypilot.targets import TARGETS
from cuypilot.workspace import OK, OUTDATED, CuypilotError, Workspace


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("target", ["opencode", "genie"])
def test_unicode_error_restores_disk_and_memory(tmp_path, target):
    ws = Workspace(tmp_path, load_catalog(), "0.6.0", target=target)
    ws.add(["python-standards"])
    path = tmp_path / next(iter(ws.lock["python-standards"]["files"]))
    path.write_bytes(b"\xff")
    before, lock = snapshot(tmp_path), copy.deepcopy(ws.lock)
    with pytest.raises(UnicodeDecodeError):
        ws.add(["python-design"])
    assert snapshot(tmp_path) == before
    assert ws.lock == lock == Workspace(tmp_path, load_catalog(), "0.6.0", target=target).lock


@pytest.mark.parametrize("target", TARGETS)
def test_orphan_block_requires_explicit_adoption(tmp_path, target):
    ws = Workspace(tmp_path, load_catalog(), "0.6.0", target=target)
    path = tmp_path / ws.instructions_path
    path.parent.mkdir(parents=True, exist_ok=True)
    original = f"# User rules\n\n{ws.start}\nKeep me.\n{ws.end}\n"
    path.write_text(original)
    with pytest.raises(CuypilotError, match="sin lockfile"):
        ws.add(["python-design"])
    assert path.read_text() == original
    assert not (tmp_path / ws.lock_path).exists()
    ws.add(["python-design"], force=True)
    assert path.read_text().startswith("# User rules\n") and "Keep me." not in path.read_text()


@pytest.mark.parametrize("target", TARGETS)
def test_base_drift_has_separate_status_plan_and_report(tmp_path, target):
    catalog = tmp_path / "catalog"
    shutil.copytree(CATALOG_DIR, catalog)
    project = tmp_path / "project"
    ws = Workspace(project, load_catalog(catalog), "0.6.0", catalog, target=target)
    ws.add(["python-design"])
    base = catalog / "base/copilot-instructions.md"
    base.write_text(base.read_text() + "\nNew convention.\n")
    assert ws.status() == {"python-design": OK}
    assert ws.block_status() == OUTDATED
    before = snapshot(project)
    plan, commands = ws.plan_update()
    assert not plan.done and not commands
    assert any(ws.instructions_path in note for note in plan.notes)
    assert snapshot(project) == before
    report = ws.update()
    assert not report.done
    assert any(ws.instructions_path in note for note in report.notes)
    assert ws.block_status() == OK


def test_update_plan_checks_conflicts_and_preserves_files(tmp_path):
    ws = Workspace(tmp_path, load_catalog(), "0.6.0")
    ws.add(["python-design"])
    path = tmp_path / next(iter(ws.lock["python-design"]["files"]))
    path.write_text("local edit")
    before = snapshot(tmp_path)
    report, _commands = ws.plan_update()
    assert "python-design" in report.skipped and not report.done
    assert snapshot(tmp_path) == before
