"""Databricks simulado: no requiere credenciales ni modifica un workspace real."""

import json
from pathlib import Path

import pytest

from cuypilot.catalog import load_catalog
from cuypilot.deploy import GenieDeployment
from cuypilot.workspace import CuypilotError, Workspace

DESTINATION = "/Workspace/Users/developer/cuypilot-demo"


class FakeDatabricks:
    def __init__(self):
        self.files = {}
        self.writes = []
        self.calls = []
        self.failure = None
        self.status_error = None

    def __call__(self, command, cwd):
        self.calls.append(command)
        action, remote = command[2:4]
        if action == "get-status":
            if self.status_error:
                return 1, self.status_error
            return (
                (0, json.dumps({"object_type": "FILE"}))
                if remote in self.files
                else (1, "RESOURCE_DOES_NOT_EXIST")
            )
        if action == "export":
            Path(command[command.index("--file") + 1]).write_bytes(self.files[remote])
            return 0, ""
        self.writes.append(command)
        if self.failure == action:
            return 1, "simulated failure"
        if action == "import":
            self.files[remote] = Path(command[command.index("--file") + 1]).read_bytes()
        elif action == "delete":
            del self.files[remote]
        return 0, ""


def workspace(path):
    return Workspace(path, load_catalog(), "0.5.0", target="genie", confirm=lambda commands: True)


def test_deploy_and_second_run_is_noop(tmp_path):
    ws, remote = workspace(tmp_path), FakeDatabricks()
    ws.add(["python-standards", "docs-writer"])
    deployment = GenieDeployment(ws, DESTINATION, profile="dev", run=remote)
    assert deployment.deploy()
    assert remote.writes[-1][3] == f"{DESTINATION}/.assistant/cuypilot.lock.json"
    assert all(command[-2:] == ("--profile", "dev") for command in remote.calls)
    lock = json.loads(remote.files[f"{DESTINATION}/.assistant/cuypilot.lock.json"])
    assert lock["items"]["docs-writer"]["type"] == "agent"
    assert "requires" in lock["items"]["docs-writer"]
    remote.writes.clear()
    assert deployment.deploy() == [] and not remote.writes
    assert any("/skills/docs-writer/SKILL.md" in path for path in remote.files)
    assert all(
        "RAW" in command and "--language" not in command
        for command in remote.writes
        if command[2] == "import"
    )


def test_dry_run_and_cancellation_do_not_write_remote(tmp_path):
    ws, remote = workspace(tmp_path), FakeDatabricks()
    ws.add(["python-design"])
    deploy = GenieDeployment(ws, DESTINATION, run=remote)
    assert deploy.deploy(dry_run=True) and not remote.writes
    ws.confirm = lambda commands: False
    with pytest.raises(CuypilotError, match="Cancelado"):
        deploy.deploy()
    assert not remote.writes


def test_deploy_rejects_foreign_remote_files(tmp_path):
    ws, remote = workspace(tmp_path), FakeDatabricks()
    ws.add(["python-design"])
    relative = next(iter(ws.lock["python-design"]["files"]))
    remote.files[f"{DESTINATION}/{relative}"] = b"foreign"
    deploy = GenieDeployment(ws, DESTINATION, run=remote)
    with pytest.raises(CuypilotError, match="ajeno o modificado"):
        deploy.deploy()
    assert not remote.writes
    deploy.deploy(force=True)
    assert remote.files[f"{DESTINATION}/{relative}"] != b"foreign"


def test_deploy_protects_remote_edits_and_preserves_foreign_instructions(tmp_path):
    ws, remote = workspace(tmp_path), FakeDatabricks()
    ws.add(["python-design"])
    remote.files[f"{DESTINATION}/AGENTS.md"] = b"# User rules\nKeep this.\n"
    deploy = GenieDeployment(ws, DESTINATION, run=remote)
    deploy.deploy()
    assert remote.files[f"{DESTINATION}/AGENTS.md"].startswith(b"# User rules\nKeep this.")
    relative = next(iter(ws.lock["python-design"]["files"]))
    remote.files[f"{DESTINATION}/{relative}"] = b"remote edit"
    remote.writes.clear()
    with pytest.raises(CuypilotError, match="ajeno o modificado"):
        deploy.deploy()
    assert not remote.writes


def test_deploy_protects_edited_remote_block(tmp_path):
    ws, remote = workspace(tmp_path), FakeDatabricks()
    ws.add(["python-design"])
    deploy = GenieDeployment(ws, DESTINATION, run=remote)
    deploy.deploy()
    agents = f"{DESTINATION}/AGENTS.md"
    remote.files[agents] = remote.files[agents].replace(b"simplest", b"most complicated")
    remote.writes.clear()
    with pytest.raises(CuypilotError, match="Bloque remoto modificado"):
        deploy.deploy()
    assert not remote.writes
    deploy.deploy(force=True)
    assert b"most complicated" not in remote.files[agents]


def test_deploy_removes_only_recorded_files_and_preserves_other_content(tmp_path):
    ws, remote = workspace(tmp_path), FakeDatabricks()
    ws.add(["python-design"])
    deploy = GenieDeployment(ws, DESTINATION, run=remote)
    deploy.deploy()
    remote.files[f"{DESTINATION}/AGENTS.md"] += b"\n## Unrelated\nKeep it.\n"
    remote.files[f"{DESTINATION}/.assistant/skills/foreign/SKILL.md"] = b"foreign skill"
    ws.remove(["python-design"])
    deploy.deploy()
    assert f"{DESTINATION}/.assistant/cuypilot.lock.json" not in remote.files
    assert remote.files[f"{DESTINATION}/.assistant/skills/foreign/SKILL.md"] == b"foreign skill"
    assert b"Unrelated" in remote.files[f"{DESTINATION}/AGENTS.md"]
    assert b"cuypilot:genie" not in remote.files[f"{DESTINATION}/AGENTS.md"]
    assert not any("--recursive" in command for command in remote.writes)


@pytest.mark.parametrize(
    "destination", ["/", "/Workspace", "relative", "/Users/x/../y", "/Users/x/", "/Users/x\\escape"]
)
def test_invalid_remote_destinations_are_rejected(tmp_path, destination):
    with pytest.raises(CuypilotError, match="carpeta absoluta específica"):
        GenieDeployment(workspace(tmp_path), destination)


def test_authentication_error_is_not_treated_as_absence(tmp_path):
    ws, remote = workspace(tmp_path), FakeDatabricks()
    ws.add(["python-design"])
    remote.status_error = "PERMISSION_DENIED"
    with pytest.raises(CuypilotError, match="PERMISSION_DENIED"):
        GenieDeployment(ws, DESTINATION, run=remote).deploy()
    assert not remote.writes


def test_malicious_remote_lock_is_rejected_before_exporting_claimed_files(tmp_path):
    ws, remote = workspace(tmp_path), FakeDatabricks()
    ws.add(["python-design"])
    remote.files[f"{DESTINATION}/.assistant/cuypilot.lock.json"] = json.dumps(
        {
            "cuypilot_version": "0.5.0",
            "target": "genie",
            "items": {
                "bad": {"type": "skill", "version": "1.0.0", "files": {"../../secret": "sha256:" + "0" * 64}}
            },
        }
    ).encode()
    with pytest.raises(CuypilotError, match="Ruta no permitida"):
        GenieDeployment(ws, DESTINATION, run=remote).deploy()
    assert not remote.writes
    assert not any("secret" in str(call) for call in remote.calls)


def test_partial_deploy_reports_failure_without_publishing_lock(tmp_path):
    ws, remote = workspace(tmp_path), FakeDatabricks()
    ws.add(["python-design"])
    remote.failure = "import"
    with pytest.raises(CuypilotError, match="Despliegue parcial"):
        GenieDeployment(ws, DESTINATION, run=remote).deploy()
    assert f"{DESTINATION}/.assistant/cuypilot.lock.json" not in remote.files


def test_modified_local_file_is_rejected_before_remote_calls(tmp_path):
    ws, remote = workspace(tmp_path), FakeDatabricks()
    ws.add(["python-design"])
    relative = next(iter(ws.lock["python-design"]["files"]))
    (tmp_path / relative).write_text("local edit")
    with pytest.raises(CuypilotError, match="Archivo local modificado"):
        GenieDeployment(ws, DESTINATION, run=remote).deploy(force=True)
    assert not remote.calls


def test_cli_exact_missing_path_message_is_supported(tmp_path):
    ws, remote = workspace(tmp_path), FakeDatabricks()
    ws.add(["python-design"])

    def runner(command, cwd):
        if command[2] == "get-status" and command[3] not in remote.files:
            return 1, f"Error: Path ({command[3]}) doesn't exist.\n"
        return remote(command, cwd)

    assert GenieDeployment(ws, DESTINATION, run=runner).deploy()
