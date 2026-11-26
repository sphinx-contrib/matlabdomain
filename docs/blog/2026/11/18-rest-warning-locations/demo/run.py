"""Build the demo project and print its warnings, paths relative to it.

Run from the docs folder::

    uv run --group docs python blog/2026/11/18-rest-warning-locations/demo/run.py
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

here = Path(__file__).parent
with tempfile.TemporaryDirectory() as out:
    cmd = [sys.executable, "-m", "sphinx", "-q", "-E", "-b", "html", here, out]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
for line in err.splitlines():
    line = re.sub(r"\x1b\[[0-9;]*m", "", line).replace(f"{here}/", "")
    if "WARNING" in line or "ERROR" in line:
        print(line)
