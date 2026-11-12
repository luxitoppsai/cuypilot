"""Publica/completa una Release sin sobrescribir assets ni mezclar wheel y checksum.

Solo se ejecuta en el job autorizado de publicación; las pruebas inyectan un ejecutor sin red.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


def run(command):
    """Ejecuta gh sin shell y devuelve código/salida."""
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def publish(tag: str, dist: Path, notes: Path, execute=run) -> None:
    """Verifica assets antes de publicar los que faltan.

    :raises RuntimeError: Si gh falla o los bytes no concuerdan con un checksum existente.
    """
    wheels = list(dist.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("Se requiere exactamente un wheel recién construido.")
    if not notes.read_text(encoding="utf-8").strip():
        raise RuntimeError("Las notas de versión están vacías.")
    wheel = wheels[0]

    def call(*args):
        code, output = execute(("gh", "release", *map(str, args)))
        if code:
            raise RuntimeError(f"Falló gh release {args[0]}: {output[-1000:]}")
        return output

    code, output = execute(("gh", "release", "view", tag, "--json", "assets"))
    exists = code == 0
    if not exists and output.strip().lower() != "release not found":
        raise RuntimeError(f"No se pudo consultar la Release: {output[-1000:]}")
    assets = {asset["name"] for asset in json.loads(output)["assets"]} if exists else set()
    if any(name.endswith(".whl") and name != wheel.name for name in assets):
        raise RuntimeError("La Release ya contiene un wheel con otro nombre; revisa el tag.")
    with TemporaryDirectory(prefix="cuypilot-release-") as directory:
        root = Path(directory)
        for name in (wheel.name, "SHA256SUMS"):
            if name in assets:
                call("download", tag, "--pattern", name, "--dir", root)
        published = root / wheel.name if wheel.name in assets else wheel
        checksum = f"{hashlib.sha256(published.read_bytes()).hexdigest()}  {wheel.name}\n"
        sums = root / "SHA256SUMS"
        if "SHA256SUMS" in assets:
            if sums.read_text(encoding="utf-8") != checksum:
                raise RuntimeError("SHA256SUMS no coincide con el wheel; no se modificó la Release.")
        else:
            sums.write_text(checksum, encoding="utf-8")
        if exists:
            for name, path in ((wheel.name, wheel), ("SHA256SUMS", sums)):
                if name not in assets:
                    call("upload", tag, path)
        else:
            call(
                "create",
                tag,
                wheel,
                sums,
                "--title",
                f"cuypilot {tag.removeprefix('v')}",
                "--notes-file",
                notes,
                "--verify-tag",
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--notes", type=Path, required=True)
    args = parser.parse_args()
    publish(args.tag, args.dist, args.notes)
