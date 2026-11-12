"""Assets de Release simulados: no requieren token ni publican nada."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("release", Path(__file__).parents[1] / "scripts/release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class Github:
    def __init__(self, exists=True, assets=None, error=None):
        self.exists = exists
        self.assets = assets or {}
        self.error = error
        self.writes = []

    def __call__(self, command):
        action = command[2]
        if action == "view":
            if self.error:
                return 1, self.error
            return (
                (0, json.dumps({"assets": [{"name": n} for n in self.assets]}))
                if self.exists
                else (1, "release not found\n")
            )
        if action == "download":
            name = command[command.index("--pattern") + 1]
            (Path(command[command.index("--dir") + 1]) / name).write_bytes(self.assets[name])
            return 0, ""
        self.writes.append(command)
        if action == "create":
            self.exists = True
            paths = command[4:6]
        else:
            paths = command[4:]
        for path in paths:
            self.assets[Path(path).name] = Path(path).read_bytes()
        return 0, ""


def checksum(data, name="cuypilot-0.6.0-py3-none-any.whl"):
    return f"{hashlib.sha256(data).hexdigest()}  {name}\n".encode()


@pytest.mark.parametrize("state", ["absent", "empty", "wheel", "checksum", "complete"])
def test_release_states_preserve_coherent_published_bytes(tmp_path, state):
    wheel = tmp_path / "cuypilot-0.6.0-py3-none-any.whl"
    wheel.write_bytes(b"new build bytes")
    notes = tmp_path / "notes.md"
    notes.write_text("Changes")
    assets = {}
    if state in ("wheel", "complete"):
        assets[wheel.name] = b"original published bytes"
    if state in ("checksum", "complete"):
        assets["SHA256SUMS"] = checksum(assets.get(wheel.name, wheel.read_bytes()))
    original = dict(assets)
    github = Github(state != "absent", assets)
    release.publish("v0.6.0", tmp_path, notes, github)
    assert github.assets["SHA256SUMS"] == checksum(github.assets[wheel.name])
    assert all(github.assets[name] == data for name, data in original.items())
    github.writes.clear()
    release.publish("v0.6.0", tmp_path, notes, github)
    assert github.writes == []


@pytest.mark.parametrize("has_wheel", [False, True])
def test_inconsistent_checksum_fails_before_any_write(tmp_path, has_wheel):
    wheel = tmp_path / "cuypilot-0.6.0-py3-none-any.whl"
    wheel.write_bytes(b"new")
    notes = tmp_path / "notes.md"
    notes.write_text("Changes")
    assets = {"SHA256SUMS": checksum(b"different")}
    if has_wheel:
        assets[wheel.name] = b"new"
    github = Github(assets=assets)
    with pytest.raises(RuntimeError, match="SHA256SUMS"):
        release.publish("v0.6.0", tmp_path, notes, github)
    assert not github.writes


def test_auth_error_is_not_absent_release(tmp_path):
    (tmp_path / "cuypilot.whl").write_bytes(b"wheel")
    notes = tmp_path / "notes.md"
    notes.write_text("Changes")
    github = Github(error="HTTP 403")
    with pytest.raises(RuntimeError, match="403"):
        release.publish("v0.6.0", tmp_path, notes, github)
    assert not github.writes
