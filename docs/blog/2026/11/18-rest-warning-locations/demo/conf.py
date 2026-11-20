"""Sphinx configuration for the demo project."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

extensions = ["helpdemo"]
exclude_patterns = ["_build"]
