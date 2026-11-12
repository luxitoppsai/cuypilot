"""Instala el wheel en un venv limpio y comprueba la CLI fuera del checkout, sin red."""

import argparse
import json
import os
import subprocess
import venv
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory


def smoke(wheel: Path, previous_wheel: Path | None = None) -> None:
    """Comprueba recursos empaquetados y ciclo de consumo en los tres destinos."""
    wheel = wheel.resolve()
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        for resource in (
            "catalog.toml",
            "base/copilot-instructions.md",
            "skills/ponytail/LICENSE",
            "skills/sphinx-setup/assets/docs/conf.py",
            "skills/sphinx-docstrings/scripts/docstring_audit.py",
        ):
            assert f"cuypilot/catalog/{resource}" in names, resource
        assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)
    with TemporaryDirectory(prefix="cuypilot-wheel-") as directory:
        root = Path(directory)
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        binary = environment / ("Scripts" if os.name == "nt" else "bin")
        python = binary / ("python.exe" if os.name == "nt" else "python")
        cli = binary / ("cuypilot.exe" if os.name == "nt" else "cuypilot")
        env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}

        def command(args, cwd=root, expected=0):
            result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
            assert result.returncode == expected, (args, result.stdout, result.stderr)
            return result.stdout

        if previous_wheel is not None:
            command(
                [
                    str(python),
                    "-I",
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--no-deps",
                    str(previous_wheel.resolve()),
                ]
            )
            upgrade = root / "upgrade"
            upgrade.mkdir()
            (upgrade / "AGENTS.md").write_text("# Team rules\nKeep these rules.\n", encoding="utf-8")
            for target in ("copilot", "opencode", "genie"):
                command([str(cli), "add", "docs-writer", "--target", target, "--path", str(upgrade)])
        command([str(python), "-I", "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)])
        if previous_wheel is not None:
            command([str(cli), "install", "--path", str(upgrade)])
            command([str(cli), "install", "--frozen", "--path", str(upgrade)])
            assert "Keep these rules." in (upgrade / "AGENTS.md").read_text(encoding="utf-8")
            print("wheel smoke: actualización desde wheel anterior pasa")
        location = command([str(python), "-I", "-c", "import cuypilot; print(cuypilot.__file__)"])
        assert environment.resolve() in Path(location.strip()).resolve().parents
        command([str(cli), "--version"])
        for target in ("copilot", "opencode", "genie"):
            project = root / target
            project.mkdir()

            def run(*args, expected=0, project=project):
                return command([str(cli), *args, "--path", str(project)], expected=expected)

            run("init", "--target", target, "--role", "docs", "--yes")
            run("add", "python-design")
            run("install", "--frozen")
            run("audit", "--ci")
            run("update", "--dry-run")
            run("outdated")
            assert "docs-writer -> sphinx-docstrings" in run("why", "sphinx-docstrings")
            assert "modificada" not in run("status")
            directory_name = {"copilot": ".github", "opencode": ".opencode", "genie": ".assistant"}[target]
            skill = project / directory_name / "skills/python-design/SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\nLocal edit.\n", encoding="utf-8")
            run("install", "--frozen", expected=1)
            run("audit", "--ci", expected=1)
            run("install", "--force", "--yes")
            run("install", "--frozen")
            lock = json.loads((project / directory_name / "cuypilot.lock.json").read_text(encoding="utf-8"))
            # Retirar también las dependencias del conjunto explícito del wizard.
            run("remove", *lock["items"])
            run("install", "--frozen")
            assert not (project / directory_name / "cuypilot.lock.json").exists()
            print(f"wheel smoke: {target} pasa")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--previous-wheel", type=Path)
    args = parser.parse_args()
    smoke(args.wheel, args.previous_wheel)
