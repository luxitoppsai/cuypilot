"""Destinos y adaptación del catálogo a los formatos documentados de cada asistente."""

from __future__ import annotations

import re
from dataclasses import dataclass

from cuypilot.catalog import Item


@dataclass(frozen=True)
class Target:
    """Formato de instalación de un asistente.

    :param name: Identificador de la CLI.
    :param label: Nombre para personas.
    :param directory: Carpeta de configuración del proyecto.
    :param instructions_path: Archivo que el asistente carga como instrucciones.
    """

    name: str
    label: str
    directory: str
    instructions_path: str

    @property
    def lock_path(self) -> str:
        """Ruta del lockfile propio del destino."""
        return f"{self.directory}/cuypilot.lock.json"

    @property
    def markers(self) -> tuple[str, str]:
        """Marcadores del bloque gestionado, aislados por destino."""
        suffix = "" if self.name == "copilot" else f":{self.name}"
        return f"<!-- cuypilot{suffix}:start -->", f"<!-- cuypilot{suffix}:end -->"

    def supports(self, item: Item) -> bool:
        """Indica si la pieza está aprobada para este destino."""
        return self.name in item.targets

    def owns(self, name: str, kind: str, path: str) -> bool:
        """Comprueba que una ruta pertenece a la pieza y a este destino."""
        if kind == "skill" or (kind == "agent" and self.name == "genie"):
            return path.startswith(f"{self.directory}/skills/{name}/")
        if kind == "agent":
            suffix = ".agent.md" if self.name == "copilot" else ".md"
            return path == f"{self.directory}/agents/{name}{suffix}"
        if kind == "instruction":
            suffix = ".instructions.md" if self.name == "copilot" else ".md"
            return path == f"{self.directory}/instructions/{name}{suffix}"
        return False

    def render(self, item: Item, catalog_dir) -> dict[str, bytes]:
        """Produce archivos del destino sin alterar el catálogo fuente.

        :param item: Pieza original, con su versión y tipo.
        :param catalog_dir: Directorio del catálogo empaquetado.
        :returns: Rutas relativas al proyecto y su contenido adaptado.
        """
        result = {}
        for relative, data in item.files(catalog_dir).items():
            if self.name == "copilot":
                result[f"{self.directory}/{relative}"] = data
                continue
            text = data.decode("utf-8") if relative.endswith(".md") else None
            if text is not None:
                text = text.replace(".github/skills/", f"{self.directory}/skills/")
                text = text.replace(".github/copilot-instructions.md", "AGENTS.md")
                if item.name == "improve-prompt":
                    invocation = (
                        "@improve-prompt" if self.name == "genie" else "use improve-prompt explicitly"
                    )
                    text = re.sub(r"(?<![\w/])/improve-prompt\b", invocation, text).replace(
                        "Copilot", self.label
                    )
            if item.type == "skill":
                if relative.endswith("/SKILL.md"):
                    meta, body = _frontmatter(text)
                    header = f"name: {item.name}\ndescription: {meta['description']}"
                    if meta.get("disable-model-invocation") == "true":
                        body = "\nUse this workflow only when the user explicitly requests it.\n" + body
                    text = f"---\n{header}\n---\n{body}"
                destination = f"{self.directory}/{relative}"
            elif item.type == "agent":
                meta, body = _frontmatter(text)
                if self.name == "genie":
                    destination = f"{self.directory}/skills/{item.name}/SKILL.md"
                    header = f"name: {item.name}\ndescription: {meta['description']}"
                    body = "\nThis is an agent workflow adapted as a Genie Code skill.\n" + body
                else:
                    destination = f"{self.directory}/agents/{item.name}.md"
                    header = f"description: {meta['description']}\nmode: all"
                text = f"---\n{header}\n---\n{body}"
            else:
                meta, body = _frontmatter(text)
                destination = f"{self.directory}/instructions/{item.name}.md"
                text = (
                    f"Apply the following rules when working with files matching {meta['applyTo']}.\n{body}"
                )
            result[destination] = text.encode("utf-8") if text is not None else data
        return result


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError("Contenido del catálogo sin frontmatter válido.")
    return dict(re.findall(r"^([A-Za-z][\w-]*):\s*(.*)$", match[1], re.MULTILINE)), match[2]


TARGETS = {
    "copilot": Target("copilot", "GitHub Copilot (VS Code)", ".github", ".github/copilot-instructions.md"),
    "opencode": Target("opencode", "OpenCode", ".opencode", "AGENTS.md"),
    "genie": Target("genie", "Genie Code (Databricks)", ".assistant", "AGENTS.md"),
}
