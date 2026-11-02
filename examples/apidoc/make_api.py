"""Write the example's API pages with the Python API of sphinx-matlab-apidoc.

``sphinx-matlab-apidoc`` takes its settings from ``docs/conf.py``. A script
sets them itself: these values give the pages of
``sphinx-matlab-apidoc -c docs``; change them (or loop over several roots)
to get other pages. Run it from anywhere::

    python make_api.py [OUTPUT_DIR]
"""

import sys
from pathlib import Path

from sphinxcontrib.mat_types import IndexSettings, build_index
from sphinxcontrib.matlab_apidoc import ApidocOptions, generate

HERE = Path(__file__).resolve().parent


def main(output_dir=HERE / "docs" / "api"):
    # What to index: matlab_src_code_project_root and the other matlab_src_*
    # values; ``source_dir`` is the Sphinx source folder.
    settings = IndexSettings(
        root=str(HERE / "src"),
        sidecar_suffixes=(".md", ".rst"),
        source_dir=str(HERE / "docs"),
    )
    # What to write: the matlab_apidoc_* values (the defaults spelled out).
    options = ApidocOptions(
        output_dir=str(output_dir),
        templatedir=str(HERE / "templates"),
        separate=False,
        maxdepth=4,
        tocfile="index",
        suffix="rst",
        remove_old=True,
    )
    result = generate(build_index(settings), options)
    print(
        f"{len(result.pages)} pages: {len(result.created)} created, "
        f"{len(result.updated)} updated, {len(result.removed)} removed."
    )


if __name__ == "__main__":
    main(*sys.argv[1:])
