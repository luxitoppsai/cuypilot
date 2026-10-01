"""Sphinx configuration (created from the cuypilot sphinx-setup skill). Replace the <...> placeholders."""

import sys
from pathlib import Path

# Make the package importable for autodoc (src/ layout; use parents[1] alone for a flat layout).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

project = "<Nombre del proyecto>"
author = "<Equipo>"
language = "es"

extensions = [
    "sphinx.ext.autodoc",  # API from Sphinx (reST) docstrings
    "sphinx.ext.autosummary",  # one page per module, generated
    "sphinx.ext.viewcode",  # links to highlighted source
    "myst_parser",  # Markdown pages (functional docs)
]

autosummary_generate = True
autodoc_default_options = {"members": True, "show-inheritance": True}
autodoc_typehints = "description"
# Heavy/cluster-only dependencies are mocked so the docs build on any laptop or CI runner.
autodoc_mock_imports = ["pyspark", "databricks", "mlflow", "delta"]

myst_enable_extensions = ["colon_fence"]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
exclude_patterns = ["_build"]

html_theme = "furo"
html_title = project

# Optional: links to Python/PySpark docs. Requires internet access at build time.
# extensions.append("sphinx.ext.intersphinx")
# intersphinx_mapping = {
#     "python": ("https://docs.python.org/3", None),
#     "pyspark": ("https://spark.apache.org/docs/latest/api/python/", None),
# }
