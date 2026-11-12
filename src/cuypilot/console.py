"""Presentación de terminal: texto legible, ancho adaptable y color opcional."""

import os
import shutil
import sys
from textwrap import fill


def paint(text: str, code: str, *, stream=None) -> str:
    """Aplica ANSI solo en una terminal que admite color; respeta NO_COLOR."""
    stream = stream if stream is not None else sys.stdout
    if "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb" or not stream.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def paragraph(text: str, indent: int = 2) -> str:
    """Ajusta prosa al ancho disponible sin dividir nombres, rutas ni comandos."""
    return fill(
        text,
        width=max(20, shutil.get_terminal_size((80, 24)).columns),
        initial_indent=" " * indent,
        subsequent_indent=" " * indent,
        break_long_words=False,
        break_on_hyphens=False,
    )
