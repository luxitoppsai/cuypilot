"""Validación del catálogo: la ejecuta el CI en cada PR (ver RFC-001 §4.7)."""

import json
import re
import warnings
from pathlib import Path

import pytest

from cuypilot.catalog import CATALOG_DIR, PATHS, Tool, load_catalog

ROOT = Path(__file__).parents[1]
CATALOG = load_catalog()
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}|ghp_[A-Za-z0-9]{20,}|dapi[0-9a-f]{20,}"
)
REVIEW_RE = re.compile(r"https?://|\bcurl\b|\bwget\b|requests\.(get|post)|urllib")
FILE_ITEMS = [i for i in CATALOG.values() if not isinstance(i, Tool)]
TOOLS = [i for i in CATALOG.values() if isinstance(i, Tool)]
THIRD_PARTY = [i for i in CATALOG.values() if i.upstream]
ALLOWED_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}
LICENSE_MARKERS = ("Permission is hereby granted", "Apache License", "Redistribution and use")
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


@pytest.mark.parametrize("item", FILE_ITEMS, ids=lambda i: i.name)
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
    registered = {Path(i.relpath).parts for i in FILE_ITEMS}
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


@pytest.mark.parametrize("item", THIRD_PARTY, ids=lambda i: i.name)
def test_third_party_is_traceable_and_licensed(item):
    up = item.upstream
    assert {"repo", "ref", "path", "license", "adapted"} <= up.keys(), "upstream incompleto"
    assert re.fullmatch(r"[0-9a-f]{40}", up["ref"]), "ref debe ser un commit sha completo"
    assert up["license"] in ALLOWED_LICENSES, f"licencia no permitida: {up['license']}"
    files = item.files()
    texts = [data.decode("utf-8", errors="ignore") for rel, data in files.items()]
    if item.type == "skill":
        assert any(rel.endswith("/LICENSE") for rel in files), "falta el LICENSE original en la carpeta"
    assert any(marker in text for text in texts for marker in LICENSE_MARKERS), "falta el texto de licencia"


@pytest.mark.parametrize("tool", TOOLS, ids=lambda i: i.name)
def test_tool_is_well_formed(tool):
    assert re.match(r"^\d+\.\d+\.\d+$", tool.version)
    assert tool.license in ALLOWED_LICENSES, f"licencia no permitida: {tool.license}"
    assert tool.check and tool.install and tool.configure, "check, install y configure son obligatorios"
    for cmd in (*tool.install, *tool.configure, *tool.uninstall, tool.check):
        assert isinstance(cmd, tuple) and all(isinstance(a, str) for a in cmd), (
            "cada comando es una lista de str"
        )
        assert not any(a in {"sh", "bash", "cmd", "powershell"} or "|" in a or "&&" in a for a in cmd), (
            "los comandos no pueden invocar un shell"
        )
    assert any(tool.version in arg for cmd in tool.install for arg in cmd), (
        "install debe fijar la versión aprobada"
    )
