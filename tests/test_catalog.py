"""Validación del catálogo: la ejecuta el CI en cada PR (ver RFC-001 §4.7)."""

import json
import re
import warnings
from pathlib import Path

import pytest

from cuypilot.catalog import CATALOG_DIR, PATHS, load_catalog

ROOT = Path(__file__).parents[1]
CATALOG = load_catalog()
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}|ghp_[A-Za-z0-9]{20,}|dapi[0-9a-f]{20,}"
)
REVIEW_RE = re.compile(r"https?://|\bcurl\b|\bwget\b|requests\.(get|post)|urllib")
REQUIRED_FRONTMATTER = {
    "skill": {"name", "description"},
    "agent": {"description"},
    "instruction": {"applyTo"},
}


def frontmatter(text: str) -> dict[str, str]:
    """Parsea las claves de primer nivel del frontmatter YAML (suficiente para validar)."""
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "falta el frontmatter (--- ... ---) al inicio del archivo"
    return dict(re.findall(r"^([A-Za-z][\w-]*):\s*(.*)$", match.group(1), re.MULTILINE))


def main_file(item) -> Path:
    path = CATALOG_DIR / item.relpath
    return path / "SKILL.md" if item.type == "skill" else path


@pytest.mark.parametrize("item", CATALOG.values(), ids=list(CATALOG))
def test_item_is_well_formed(item):
    assert NAME_RE.match(item.name), "nombre: solo minúsculas, dígitos y guiones (máx. 64)"
    assert item.type in PATHS
    assert re.match(r"^\d+\.\d+\.\d+$", item.version), "version debe ser semver X.Y.Z"
    assert item.description.strip()
    assert main_file(item).is_file(), f"no existe {main_file(item).relative_to(CATALOG_DIR)}"

    meta = frontmatter(main_file(item).read_text(encoding="utf-8"))
    assert REQUIRED_FRONTMATTER[item.type] <= meta.keys(), f"frontmatter incompleto: {meta.keys()}"
    if item.type == "skill":
        assert meta["name"] == item.name, "el `name` del SKILL.md debe coincidir con la carpeta"
        assert 0 < len(meta["description"]) <= 1024


@pytest.mark.parametrize("item", CATALOG.values(), ids=list(CATALOG))
def test_item_content_is_safe(item):
    for rel, data in item.files().items():
        text = data.decode("utf-8", errors="ignore")
        assert not SECRET_RE.search(text), f"posible secreto en {rel}"
        if REVIEW_RE.search(text) or not rel.endswith(".md"):
            warnings.warn(
                f"{rel}: contiene red o scripts, requiere revisión manual de seguridad", stacklevel=1
            )


def test_no_unregistered_files():
    registered = {Path(i.relpath).parts for i in CATALOG.values()}
    for kind in ("skills", "agents", "instructions"):
        for entry in (CATALOG_DIR / kind).iterdir():
            assert (kind, entry.name) in registered, f"{kind}/{entry.name} no está registrado en catalog.toml"


def test_requires_exist_and_have_no_cycles():
    def visit(name, path):
        assert name in CATALOG, f"requires apunta a una pieza inexistente: {name}"
        assert name not in path, f"ciclo en requires: {' -> '.join([*path, name])}"
        for dep in CATALOG[name].requires:
            visit(dep, [*path, name])

    for name in CATALOG:
        visit(name, [])


WITH_EVALS = [i for i in CATALOG.values() if i.type in ("skill", "agent")]


@pytest.mark.parametrize("item", WITH_EVALS, ids=lambda i: i.name)
def test_has_evals(item):
    path = ROOT / "evals" / f"{item.name}.json"
    assert path.is_file(), f"falta evals/{item.name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    kinds = [c["kind"] for c in data["cases"]]
    assert data["item"] == item.name
    assert len(kinds) >= 3 and "trigger" in kinds and "no-trigger" in kinds
    assert all(c["prompt"] and c["expected"] for c in data["cases"])


def test_base_instructions_exist():
    assert (CATALOG_DIR / "base" / "copilot-instructions.md").read_text(encoding="utf-8").strip()
