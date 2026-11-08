"""Group the warnings of a Sphinx build by type, with counts and examples.

Usage: python group_warnings.py WARNINGS_FILE [--show N]

WARNINGS_FILE is the file of ``sphinx-build -w``. Warnings with a type
(``[mat.not_callable]``, ``[ref.class]``) are grouped by it; the others by
their message with quoted names replaced, so that the same problem in many
files is one group.
"""

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

LINE = re.compile(
    r"^(?:(?P<loc>.*?): )?(?P<level>WARNING|ERROR|CRITICAL|SEVERE): "
    r"(?P<msg>.*?)(?: \[(?P<type>[\w.]+)\])?$"
)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("warnings", type=Path)
    parser.add_argument(
        "--show", type=int, default=3, help="examples per group (default 3)"
    )
    args = parser.parse_args()
    groups = Counter()
    examples = defaultdict(list)
    other = 0
    for line in args.warnings.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines():
        m = LINE.match(line)
        if not m:
            other += 1  # continuation lines of multi-line messages
            continue
        key = m["type"] or re.sub(r"[`'\"][^`'\"]*[`'\"]", "<x>", m["msg"])[:90]
        key = f"{m['level']}: {key}"
        groups[key] += 1
        if len(examples[key]) < args.show:
            examples[key].append(line[:240])
    for key, count in groups.most_common():
        print(f"{count:6}  {key}")
        for example in examples[key]:
            print(f"          {example}")
    print(
        f"\n{sum(groups.values())} warning(s) in {len(groups)} group(s); "
        f"{other} other line(s)"
    )


if __name__ == "__main__":
    main()
