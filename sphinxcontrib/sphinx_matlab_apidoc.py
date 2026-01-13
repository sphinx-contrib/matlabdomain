#!/usr/bin/env python3
"""sphinx-matlab-apidoc.
~~~~~~~~~~~~~~~~~~~~

Generate reStructuredText files for MATLAB source code documentation.

Similar to sphinx-apidoc but specifically designed for MATLAB projects.
Generates RST files per namespace and limits to 50 code files per page.

:copyright: Copyright 2025 by the sphinxcontrib-matlabdomain team.
:license: BSD, see LICENSE for details.
"""

import argparse
import os
import sys
from collections import defaultdict
from importlib.metadata import version
from pathlib import Path

from tree_sitter import Parser

from sphinxcontrib.mat_tree_sitter_parser import ML_LANG

MATLAB_EXTENSIONS = {".m", ".mlapp"}
MAX_FILES_PER_PAGE = 50


def find_matlab_files(source_dir: Path) -> list[Path]:
    """Find all MATLAB files in the source directory."""
    matlab_files = []
    for root, dirs, files in os.walk(source_dir):
        # Skip hidden directories and common non-source directories
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".") and d not in ["private", "__pycache__"]
        ]

        for file in files:
            if any(file.endswith(ext) for ext in MATLAB_EXTENSIONS):
                file_path = Path(root) / file
                matlab_files.append(file_path)

    return sorted(matlab_files)


def get_namespace_from_path(file_path: Path, source_dir: Path) -> str:
    """Extract namespace from file path.

    MATLAB namespaces are indicated by + prefix in directory names.
    For example: +mypackage/+subpackage/MyClass.m -> mypackage.subpackage
    """
    relative_path = file_path.relative_to(source_dir)
    parts = list(relative_path.parts[:-1])  # Exclude filename

    namespace_parts = []
    for part in parts:
        if part.startswith("+") or part.startswith("@"):
            namespace_parts.append(part[1:])
        else:
            namespace_parts.append(part)

    if namespace_parts:
        return ".".join(namespace_parts)
    return "root"


def organize_by_namespace(
    matlab_files: list[Path], source_dir: Path
) -> dict[str, list[Path]]:
    """Organize MATLAB files by their namespace."""
    namespace_files = defaultdict(list)

    for file_path in matlab_files:
        namespace = get_namespace_from_path(file_path, source_dir)
        namespace_files[namespace].append(file_path)

    return dict(namespace_files)


def sanitize_module_name(relative_path: Path) -> str:
    """Convert a MATLAB file path to a matlabdomain target name."""
    module_name = str(relative_path).replace(os.sep, ".")
    # Remove + for packages, keep @ for class folders
    module_name = module_name.replace("+", "")
    # Sanitize special characters
    module_name = module_name.replace("-", "_")
    module_name = module_name.replace("(", "").replace(")", "").replace(" ", "_")
    # Prefix leading digits in path segments
    parts = module_name.split(".")
    parts = ["m_" + p if p and p[0].isdigit() else p for p in parts]
    return ".".join(parts)


def detect_item_type(file_path: Path) -> str:
    """Determine whether the MATLAB file is a class, function, script, or app.

    Uses tree-sitter parser for accurate detection, matching the logic in mat_types.py.
    """
    if file_path.suffix.lower() == ".mlapp":
        return "app"

    try:
        with open(file_path, "rb") as f:
            code = f.read()

        # Initialize parser based on tree_sitter version
        tree_sitter_ver = tuple([int(sec) for sec in version("tree_sitter").split(".")])
        if tree_sitter_ver[1] == 21:
            parser = Parser()
            parser.set_language(ML_LANG)
        else:
            parser = Parser(ML_LANG)

        tree = parser.parse(code)

        # Check if it's a class
        q_is_class = ML_LANG.query("(class_definition)")
        if q_is_class.matches(tree.root_node):
            return "class"

        # Check if it's a function
        q_is_function = ML_LANG.query(
            r"""(source_file [(comment) "\n"]* (function_definition))"""
        )
        if q_is_function.matches(tree.root_node):
            return "function"

        # Otherwise it's a script
        return "script"

    except (OSError, Exception):
        # If parsing fails, default to script
        return "script"


def generate_module_rst(
    items: list[tuple[str, str]],
    namespace: str,
    page_num: int = 0,
    total_pages: int = 1,
) -> str:
    """Generate RST content for a module/namespace page."""
    is_root = namespace == "root"
    ns_title = "Global Namespace" if is_root else f"{namespace} Namespace"
    if total_pages > 1:
        ns_title = f"{ns_title} (Page {page_num + 1}/{total_pages})"

    lines = [
        ns_title,
        "=" * len(ns_title),
        "",
        ".. contents:: Table of Contents",
        "   :depth: 10",
        "   :local:",
        "",
    ]

    grouped = {"class": [], "function": [], "script": [], "app": []}
    for name, kind in items:
        grouped.setdefault(kind, []).append(name)

    sections = [
        (
            "Classes",
            "class",
            "mat:autoclass",
            [
                "   :show-inheritance:",
                "   :members:",
                "   :private-members:",
                "   :special-members:",
                "   :undoc-members:",
            ],
        ),
        ("Functions", "function", "mat:autofunction", []),
        ("Scripts", "script", "mat:autoscript", []),
        ("Apps", "app", "mat:autoscript", []),
    ]

    for section_title, key, directive, extra_opts in sections:
        if not grouped.get(key):
            continue
        lines.extend([section_title, "-" * len(section_title), ""])
        for target in sorted(grouped[key]):
            heading = f"Function Reference: {target}"
            lines.append(heading)
            lines.append("^" * len(heading))
            lines.append("")
            lines.append(f".. {directive}:: {target}")
            lines.extend(extra_opts)
            if extra_opts:
                lines.append("")
            lines.append("")

    return "\n".join(lines)


def get_rst_filename(namespace: str, page_num: int = 0, total_pages: int = 1) -> str:
    """Generate RST filename for a namespace and page number."""
    base = "global_namespace" if namespace == "root" else namespace.replace(".", "_")

    if total_pages > 1:
        return f"{base}_{page_num + 1}.rst"
    return f"{base}.rst"


def generate_index_rst(
    namespace_items: dict[str, list[tuple[str, str]]], max_files_per_page: int
) -> str:
    """Generate the main index.rst file."""
    lines = [
        "MATLAB API Documentation",
        "========================",
        "",
        ".. toctree::",
        "   :maxdepth: 2",
        "   :caption: Modules:",
        "",
    ]

    # Sort namespaces
    sorted_namespaces = sorted(namespace_items.keys())

    for namespace in sorted_namespaces:
        items = namespace_items[namespace]
        total_pages = (len(items) + max_files_per_page - 1) // max_files_per_page

        if total_pages > 1:
            for page_num in range(total_pages):
                rst_file = get_rst_filename(namespace, page_num, total_pages)
                lines.append(f"   {rst_file[:-4]}")  # Remove .rst extension
        else:
            rst_file = get_rst_filename(namespace, 0, 1)
            lines.append(f"   {rst_file[:-4]}")

    lines.append("")

    # Add indices and tables
    lines.extend(
        [
            "Indices and tables",
            "==================",
            "",
            "* :ref:`genindex`",
            "* :ref:`modindex`",
            "* :ref:`search`",
            "",
        ]
    )

    return "\n".join(lines)


def write_rst_files(
    namespace_items: dict[str, list[tuple[str, str]]],
    output_dir: Path,
    max_files_per_page: int,
    dry_run: bool = False,
) -> None:
    """Write RST files for all namespaces."""
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Generate index.rst
    index_content = generate_index_rst(namespace_items, max_files_per_page)
    index_path = output_dir / "index.rst"

    if dry_run:
        print(f"Would create: {index_path}")
    else:
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)
        print(f"Created: {index_path}")

    # Generate RST files for each namespace
    for namespace, items in sorted(namespace_items.items()):
        total_pages = (len(items) + max_files_per_page - 1) // max_files_per_page

        print(f"\nNamespace '{namespace}': {len(items)} files, {total_pages} page(s)")

        for page_num in range(total_pages):
            start_idx = page_num * max_files_per_page
            end_idx = min(start_idx + max_files_per_page, len(items))
            page_items = items[start_idx:end_idx]

            rst_content = generate_module_rst(
                page_items, namespace, page_num, total_pages
            )
            rst_filename = get_rst_filename(namespace, page_num, total_pages)
            rst_path = output_dir / rst_filename

            if dry_run:
                print(f"  Would create: {rst_path} ({len(page_items)} files)")
            else:
                with open(rst_path, "w", encoding="utf-8") as f:
                    f.write(rst_content)
                print(f"  Created: {rst_path} ({len(page_items)} files)")


def main():
    """Run sphinx-matlab-apidoc."""
    parser = argparse.ArgumentParser(
        description="Generate reStructuredText files for MATLAB source code documentation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  sphinx-matlab-apidoc -o docs/source /path/to/matlab/code
  sphinx-matlab-apidoc -o docs/source /path/to/matlab/code --dry-run
        """,
    )

    parser.add_argument(
        "source_dir", type=Path, help="Path to MATLAB source code directory"
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("docs/source"),
        help="Output directory for RST files (default: docs/source)",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Do not create files, just show what would be done",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="Overwrite existing files"
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=50,
        help="Maximum files per page (default: 50)",
    )

    args = parser.parse_args()

    # Update max files per page if specified
    max_files_per_page = args.max_files

    # Validate source directory
    if not args.source_dir.exists():
        print(
            f"Error: Source directory does not exist: {args.source_dir}",
            file=sys.stderr,
        )
        return 1

    if not args.source_dir.is_dir():
        print(
            f"Error: Source path is not a directory: {args.source_dir}", file=sys.stderr
        )
        return 1

    # Check if output directory exists and is not empty
    if args.output_dir.exists() and not args.force and not args.dry_run:
        if any(args.output_dir.iterdir()):
            response = input(
                f"Output directory {args.output_dir} is not empty. Continue? [y/N] "
            )
            if response.lower() not in ["y", "yes"]:
                print("Aborted.")
                return 0

    print(f"Scanning MATLAB files in: {args.source_dir}")

    # Find all MATLAB files
    matlab_files = find_matlab_files(args.source_dir)

    if not matlab_files:
        print("Warning: No MATLAB files found!")
        return 0

    print(f"Found {len(matlab_files)} MATLAB file(s)")

    # Organize by namespace and type
    namespace_files = organize_by_namespace(matlab_files, args.source_dir)
    namespace_items: dict[str, list[tuple[str, str]]] = {}
    for ns, files in namespace_files.items():
        entries: list[tuple[str, str]] = []
        for file_path in files:
            rel = file_path.relative_to(args.source_dir).with_suffix("")
            module_name = sanitize_module_name(rel)
            item_type = detect_item_type(file_path)
            entries.append((module_name, item_type))
        namespace_items[ns] = entries

    print(f"Organized into {len(namespace_items)} namespace(s)")

    # Write RST files
    write_rst_files(
        namespace_items,
        args.output_dir,
        max_files_per_page,
        args.dry_run,
    )

    if args.dry_run:
        print("\nDry run completed. No files were created.")
    else:
        print(f"\nRST files generated in: {args.output_dir}")
        print("You can now run 'sphinx-build' to generate documentation.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
