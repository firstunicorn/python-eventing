"""Sphinx configuration for the messagekit library."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

project = "messagekit"
author = "FirstUnicorn"
copyright = "2026, FirstUnicorn"
root_doc = "index"
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    # "autoapi.extension",  # Disabled due to KeyError on messagekit.config.settings
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_llms_txt",
]
templates_path: list[str] = []
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_title = project
html_static_path: list[str] = []
html_theme_options = {
    "top_of_page_buttons": [],
    "navigation_with_keys": True,
}

# Furo theme automatically generates sidebar navigation from toctree
# No need for explicit html_sidebars configuration

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "member-order": "bysource",
}
autodoc_typehints = "description"
always_document_param_types = True
typehints_use_rtype = True
typehints_defaults = "comma"

autoapi_type = "python"
autoapi_dirs = [str(SRC_DIR / "messagekit")]
autoapi_root = "autoapi"
autoapi_add_toctree_entry = True
autoapi_keep_files = False  # Don't keep files to avoid stale references
autoapi_member_order = "bysource"
autoapi_python_use_implicit_namespaces = True
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]
autoapi_ignore = ["*/conftest.py", "*/test_*.py"]  # Ignore test files

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_use_param = True
napoleon_use_rtype = True

myst_heading_anchors = 3

llms_txt_title = project
llms_txt_summary = (
    "Universal messaging primitives for canonical events, transactional outbox "
    "publishing, Kafka integration, and service wiring."
)
