"""Lazy index and parse, source patterns and parallel reads (plan.md Phase 6)."""

import os
import pickle
import subprocess
import sys
import time

import pytest
import sphinx.builders
from sphinx.errors import ConfigError

from sphinxcontrib import mat_types

CONF = (
    'extensions = ["sphinx.ext.autodoc", "sphinxcontrib.matlab"]\n'
    'matlab_src_code_project_root = "."\n'
    'primary_domain = "mat"\n'
)
FUNCTION = "function {name}\n% {help}\nend\n"
# A class by its first line, a script for tree-sitter (mat.invalid_matlab).
BROKEN = "classdef Broken\n% BROKEN HELP\nmethods\nfunction obj = Broken()\nend\n"
FILES = {
    "used.m": FUNCTION.format(name="used", help="USED HELP"),
    "unused.m": FUNCTION.format(name="unused", help="UNUSED HELP"),
    "Broken.m": BROKEN,
    "+pkg/Cls.m": "classdef Cls\n% CLS HELP\nmethods\nfunction go(~)\nend\nend\nend\n",
    "+pkg/other.m": FUNCTION.format(name="other", help="OTHER HELP"),
    "tests/test_x.m": FUNCTION.format(name="test_x", help="TEST HELP"),
    "src/lib/deep.m": FUNCTION.format(name="deep", help="DEEP HELP"),
}


def write(root, files, rst="Index\n=====\n", conf=CONF):
    for path, content in {**files, "conf.py": conf, "index.rst": rst}.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)


def refs(app):
    return sorted(r["reference"] for r in app.env.domaindata["mat"]["index"].values())


def folders(app):
    return sorted(
        r for r in app.env.get_domain("mat").entities_table if r.endswith("/")
    )


@pytest.fixture
def parsed(monkeypatch):
    """Record every file the handlers parse."""
    calls = []
    for name in ("parse_mfile", "parse_mlappfile"):
        original = getattr(mat_types.MatObject, name)

        def counting(path, *args, _original=original, **kwargs):
            calls.append(str(path))
            return _original(path, *args, **kwargs)

        monkeypatch.setattr(mat_types.MatObject, name, staticmethod(counting))
    return calls


# --- lazy parse -------------------------------------------------------------


def test_only_used_files_are_parsed(make_app, tmp_path, parsed):
    write(tmp_path, FILES, "Index\n=====\n\n.. mat:autofunction:: used\n")
    app = make_app(srcdir=tmp_path)
    app.build()
    assert parsed == [str(tmp_path / "used.m")]
    assert refs(app) == sorted(FILES)
    assert "USED HELP" in (app.outdir / "index.html").read_text()
    # No parse-stage warning for the unused broken class.
    assert "WARNING" not in app.warning.getvalue()


def test_parse_warnings_once_per_build(make_app, tmp_path, parsed):
    pages = {
        f"{name}.rst": f":orphan:\n\n{name}\n====\n\n.. mat:autoscript:: Broken.m\n"
        "   :noindex:\n"
        for name in ("one", "two")
    }
    write(
        tmp_path, {**FILES, **pages}, "Index\n=====\n\n.. mat:autoscript:: Broken.m\n"
    )
    app = make_app(srcdir=tmp_path)
    app.build()
    assert parsed == [str(tmp_path / "Broken.m")]
    assert app.warning.getvalue().count("may be invalid MATLAB") == 1


def test_member_lookup_by_file_name_does_not_parse_again(make_app, tmp_path, parsed):
    # plan.md Phase 5 follow-up: a lookup after the index stage parsed and
    # warned again.
    write(tmp_path, FILES, "Index\n=====\n\n.. mat:autoscript:: Broken.m\n")
    app = make_app(srcdir=tmp_path)
    app.build()
    dom = app.env.get_domain("mat")
    warnings = app.warning.getvalue()
    broken = mat_types.resolve(dom, "Broken.m")
    assert dom.entities_table["./"].getter("Broken.m") is broken
    assert dom.entities_table["./"].getter("Broken") is broken
    assert mat_types.MatObject.matlabify("Broken") is broken
    assert parsed == [str(tmp_path / "Broken.m")]
    assert app.warning.getvalue() == warnings


def test_source_text_cache(make_app, tmp_path, monkeypatch, parsed):
    opened = []
    real_open = open

    def counting_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(mat_types, "open", counting_open, raising=False)
    write(tmp_path, FILES, "Index\n=====\n\n.. mat:autofunction:: used\n")
    app = make_app(srcdir=tmp_path)
    app.build()
    assert parsed == [str(tmp_path / "used.m")]
    assert opened == []
    assert "USED HELP" in (app.outdir / "index.html").read_text()


# --- include and exclusion patterns ----------------------------------------


@pytest.mark.parametrize(
    ("overrides", "expected_refs", "expected_folders"),
    [
        (
            {"matlab_src_include_patterns": ["src/**", "+pkg/*.m"]},
            ["+pkg/Cls.m", "+pkg/other.m", "src/lib/deep.m"],
            ["+pkg/", "./", "src/", "src/lib/"],
        ),
        (
            {"matlab_src_include_patterns": ["src/../+pkg/*.m", "./used.m"]},
            ["+pkg/Cls.m", "+pkg/other.m", "used.m"],
            ["+pkg/", "./"],
        ),
        (
            {"matlab_src_exclude_patterns": ["**/tests/**"]},
            sorted(set(FILES) - {"tests/test_x.m"}),
            ["+pkg/", "./", "src/", "src/lib/"],
        ),
        (
            {"matlab_src_exclude_patterns": ["**/lib", "**/Broken.m"]},
            sorted(set(FILES) - {"src/lib/deep.m", "Broken.m"}),
            ["+pkg/", "./", "src/", "tests/"],
        ),
        ({"matlab_src_include_patterns": []}, [], ["./"]),
        # Case-sensitive on every OS, like the path references it matches.
        ({"matlab_src_include_patterns": ["+PKG/**", "Used.m"]}, [], ["./"]),
    ],
    ids=["include", "dotdot", "exclude", "exclude-folder", "empty", "case"],
)
def test_source_patterns(
    make_app, tmp_path, overrides, expected_refs, expected_folders
):
    write(tmp_path, FILES)
    app = make_app(srcdir=tmp_path, confoverrides=overrides)
    app.build()
    assert refs(app) == expected_refs
    assert folders(app) == expected_folders


def test_changing_patterns_reindexes(make_app, tmp_path, parsed):
    write(tmp_path, FILES, "Index\n=====\n\n.. mat:autofunction:: test_x\n")
    exclude = {"matlab_src_exclude_patterns": ["tests/**"]}
    app = make_app(srcdir=tmp_path, confoverrides=exclude)
    app.build()
    assert "tests/test_x.m" not in refs(app)
    assert "TEST HELP" not in (app.outdir / "index.html").read_text()

    # A config change re-reads every page with a fresh index and parses.
    parsed.clear()
    app2 = make_app(srcdir=tmp_path)
    app2.build()
    assert "tests/test_x.m" in refs(app2)
    assert parsed == [str(tmp_path / "tests" / "test_x.m")]
    assert "TEST HELP" in (app2.outdir / "index.html").read_text()


def test_excluded_files_are_not_found(make_app, tmp_path):
    write(
        tmp_path,
        FILES,
        "Index\n=====\n\n.. mat:autofunction:: test_x\n\n.. mat:autofunction:: used\n",
    )
    app = make_app(
        srcdir=tmp_path,
        confoverrides={"matlab_src_exclude_patterns": ["tests/**"]},
    )
    app.build()
    warnings = app.warning.getvalue()
    assert "don't know which object to document for 'test_x'" in warnings
    assert "USED HELP" in (app.outdir / "index.html").read_text()


@pytest.mark.parametrize(
    "pattern",
    [
        "/abs/**",
        "C:/x/**",
        "C:x/*.m",
        "//server/share/**",
        "src\\**",
        "..",
        "../x/**",
        "src/../../x/**",
        "**/../x.m",
        "src/..",
        "",
    ],
)
@pytest.mark.parametrize(
    "option", ["matlab_src_include_patterns", "matlab_src_exclude_patterns"]
)
def test_patterns_must_stay_below_the_root(make_app, tmp_path, option, pattern):
    write(tmp_path, FILES)
    with pytest.raises(ConfigError, match=option):
        make_app(srcdir=tmp_path, confoverrides={option: [pattern]})


@pytest.mark.parametrize(
    "overrides",
    [
        {"matlab_src_include_patterns": ["src/**"]},
        {"matlab_src_include_patterns": []},
        {"matlab_src_exclude_patterns": ["tests/**"]},
    ],
)
def test_patterns_need_the_project_root(make_app, tmp_path, overrides):
    write(tmp_path, FILES, conf=CONF.replace('matlab_src_code_project_root = "."', ""))
    with pytest.raises(ConfigError, match="need matlab_src_code_project_root"):
        make_app(srcdir=tmp_path, confoverrides=overrides)


def test_default_patterns_without_a_root(make_app, tmp_path):
    write(tmp_path, FILES, conf=CONF.replace('matlab_src_code_project_root = "."', ""))
    app = make_app(
        srcdir=tmp_path, confoverrides={"matlab_src_include_patterns": ["**/*"]}
    )
    app.build()
    assert refs(app) == []


def test_patterns_must_be_a_list(make_app, tmp_path):
    write(tmp_path, FILES, conf=CONF + 'matlab_src_include_patterns = "src/**"\n')
    with pytest.raises(ConfigError, match="must be a list"):
        make_app(srcdir=tmp_path)


def test_within(tmp_path):
    import ntpath
    import posixpath

    assert mat_types._within(r"C:\root\a", r"C:\root", ntpath)
    assert mat_types._within(r"c:\ROOT\a", r"C:\root", ntpath)
    assert not mat_types._within(r"D:\root\a", r"C:\root", ntpath)
    assert not mat_types._within(r"C:\rootx", r"C:\root", ntpath)
    assert mat_types._within("/root/a", "/root", posixpath)
    assert not mat_types._within("/Root/a", "/root", posixpath)
    assert not mat_types._within("/rootx", "/root", posixpath)


# --- links (symbolic links; junctions on Windows) ---------------------------


LINK_KINDS = ["symlink", *(["junction"] if sys.platform == "win32" else [])]


def _link(target, link, kind):
    """Create a folder link; skip when the OS does not allow it here."""
    if kind == "junction":
        assert sys.platform == "win32"
        import _winapi

        _winapi.CreateJunction(str(target), str(link))
        return
    try:
        os.symlink(target, link, target_is_directory=True)
    except (OSError, NotImplementedError) as err:
        pytest.skip(
            f"cannot create a symbolic link here ({err}); needs Windows "
            "Developer Mode, covered by the Linux handoff"
        )


def _file_link(target, link):
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError) as err:
        pytest.skip(
            f"cannot create a file symbolic link here ({err}); needs Windows "
            "Developer Mode, covered by the Linux handoff"
        )


@pytest.fixture
def linked(tmp_path):
    root, outside = tmp_path / "root", tmp_path / "outside"
    write(root, FILES)
    write(outside, {"far.m": FUNCTION.format(name="far", help="FAR HELP")})
    (outside / "conf.py").unlink()
    (outside / "index.rst").unlink()
    return root, outside


@pytest.mark.parametrize("kind", LINK_KINDS)
def test_link_out_of_the_root_is_skipped(make_app, linked, kind):
    root, outside = linked
    _link(outside, root / "away", kind)
    app = make_app(srcdir=root)
    app.build()
    assert "away/far.m" not in refs(app)
    assert "away/" not in folders(app)
    warnings = app.warning.getvalue()
    assert warnings.count("[mat.outside_root]") == 1
    assert "away/ links to " in warnings


def test_file_link_out_of_the_root_is_skipped(make_app, linked):
    root, outside = linked
    _file_link(outside / "far.m", root / "far.m")
    app = make_app(srcdir=root)
    app.build()
    assert "far.m" not in refs(app)
    assert "far.m links to " in app.warning.getvalue()


@pytest.mark.parametrize("kind", LINK_KINDS)
def test_link_inside_the_root_is_followed(make_app, linked, kind):
    root, _ = linked
    _link(root / "src", root / "alias", kind)
    app = make_app(srcdir=root)
    app.build()
    assert {"alias/lib/deep.m", "src/lib/deep.m"} <= set(refs(app))
    assert "outside_root" not in app.warning.getvalue()


@pytest.mark.parametrize("kind", LINK_KINDS)
def test_pattern_through_a_link_out_of_the_root_raises(make_app, linked, kind):
    root, outside = linked
    _link(outside, root / "away", kind)
    with pytest.raises(ConfigError, match="outside matlab_src_code_project_root"):
        make_app(
            srcdir=root, confoverrides={"matlab_src_include_patterns": ["away/**"]}
        )


# Links that make a cycle inside the root: (link, target) below the root.
LINK_CYCLES = {
    "to-parent": [("a/loop", "")],
    "to-itself": [("a/self", "a")],
    "two-to-parent": [("a/loop1", ""), ("a/loop2", "")],
    "mutual": [("a/x", "b"), ("b/y", "a")],
}
# Unbounded, the walk lists each folder once per path the OS resolves (about
# 40 links on Linux): 41 copies for one cycle, 2**41 - 1 for two.
MAX_LISTED_FOLDERS = 50


def _cycle_tree(root, cycle, kind):
    for path in ("top.m", "a/fa.m", "b/fb.m"):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        stem = path.rpartition("/")[2][:-2]
        (root / path).write_text(FUNCTION.format(name=stem, help="HELP"))
    for link, target in LINK_CYCLES[cycle]:
        _link(root / target, root / link, kind)


@pytest.mark.parametrize("kind", LINK_KINDS)
@pytest.mark.parametrize("cycle", sorted(LINK_CYCLES))
def test_link_cycle_is_walked_once(tmp_path, monkeypatch, cycle, kind):
    root = tmp_path / "root"
    _cycle_tree(root, cycle, kind)
    listed = [0]
    original = mat_types._Indexer.list

    def bounded(self, mod, *args):
        listed[0] += 1
        if listed[0] > MAX_LISTED_FOLDERS:
            raise AssertionError(f"the walk repeats the tree: {mod.ref[:80]}...")
        return original(self, mod, *args)

    monkeypatch.setattr(mat_types._Indexer, "list", bounded)
    source_index = mat_types.build_index(mat_types.IndexSettings(str(root)))
    # No path passes through the same real folder twice.
    for record in source_index.index.values():
        parts = record["reference"].split("/")[:-1]
        chain = [
            os.path.realpath(os.path.join(root, *parts[:n]))
            for n in range(len(parts) + 1)
        ]
        assert len(set(chain)) == len(chain), record["reference"]


# What the walk indexes and warns for each cycle: a link to the folder it is
# in or to a folder above it (up to the root) is not followed.
CYCLE_RESULTS = {
    "to-parent": (["a/fa.m", "b/fb.m", "top.m"], ["a/loop/"]),
    "to-itself": (["a/fa.m", "b/fb.m", "top.m"], ["a/self/"]),
    "two-to-parent": (["a/fa.m", "b/fb.m", "top.m"], ["a/loop1/", "a/loop2/"]),
    # Each link is followed once, from the other folder; the second link on
    # that path leads back.
    "mutual": (
        ["a/fa.m", "a/x/fb.m", "b/fb.m", "b/y/fa.m", "top.m"],
        ["a/x/y/", "b/y/x/"],
    ),
}


@pytest.mark.parametrize("kind", LINK_KINDS)
@pytest.mark.parametrize("cycle", sorted(CYCLE_RESULTS))
def test_link_cycle_warns_once_per_link(tmp_path, cycle, kind):
    root = tmp_path / "root"
    _cycle_tree(root, cycle, kind)
    logged = []

    def warn(subtype, message, location=None):
        logged.append((subtype, message))

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(mat_types, "_warn", warn)
        source_index = mat_types.build_index(mat_types.IndexSettings(str(root)))
    indexed, links = CYCLE_RESULTS[cycle]
    assert sorted(r["reference"] for r in source_index.index.values()) == indexed
    assert sorted(m.split(" ")[0] for s, m in logged) == links
    assert {s for s, _ in logged} == {"link_cycle"}
    target = {
        "a/loop/": root,
        "a/loop1/": root,
        "a/loop2/": root,
        "a/self/": root / "a",
        "a/x/y/": root / "a",
        "b/y/x/": root / "b",
    }
    for _, message in logged:
        ref = message.split(" ")[0]
        real = os.path.realpath(target[ref])
        assert message == (
            f"{ref} links to {real}, a folder that contains it; the link is not "
            "followed."
        )


def test_link_cycle_through_the_root_in_a_build(make_app, tmp_path):
    root = tmp_path / "root"
    files = {
        "top.m": FUNCTION.format(name="top", help="TOP HELP"),
        "a/fa.m": FUNCTION.format(name="fa", help="FA HELP"),
        "doc.rst": "Doc\n===\n",
    }
    write(root, files)
    write(root / "docs", {}, conf=CONF.replace('"."', '".."'))
    _link(root, root / "a" / "up", "symlink")
    app = make_app(
        srcdir=root / "docs",
        confoverrides={"matlab_src_sidecar_suffixes": [".rst"]},
    )
    app.build()
    assert sorted(refs(app)) == ["a/fa.m", "top.m"]
    assert "a/up/" not in folders(app)
    warnings = app.warning.getvalue()
    # The quiet walk of the sidecar docs skips the cycle too, without a
    # second warning.
    assert warnings.count("[mat.link_cycle]") == 1, warnings
    assert "a/up/ links to " in warnings


def test_link_cycle_in_the_sidecar_walk(tmp_path):
    root = tmp_path / "root"
    (root / "a").mkdir(parents=True)
    (root / "a" / "doc.rst").write_text("Doc\n===\n")
    _link(root, root / "a" / "up", "symlink")
    settings = mat_types.IndexSettings(str(root), sidecar_suffixes=(".rst",))
    assert mat_types.sidecar_paths(settings) == [str(root / "a" / "doc.rst")]


# --- parallel reads ----------------------------------------------------------


class ForkLikeTasks:
    """Stand-in for ``sphinx.util.parallel.ParallelTasks`` where Sphinx cannot
    fork (Windows): each read task runs on a pickled copy of the environment,
    as a forked worker would, and returns it to the main process's merge.
    """

    app = None

    def __init__(self, nproc):
        self.tasks = []

    def add_task(self, task_func, arg=None, result_func=None):
        self.tasks.append((task_func, arg, result_func))

    def join(self):
        app = self.app
        assert app is not None
        for func, arg, result_func in self.tasks:
            if func.__name__ != "read_process":
                ret = func(arg)
            else:
                main = app.env
                worker = pickle.loads(pickle.dumps(main, pickle.HIGHEST_PROTOCOL))
                worker.setup(app)
                if hasattr(main, "_builder_cls"):  # Sphinx >= 8.2
                    worker._builder_cls = main._builder_cls
                cache = dict(mat_types.MatModuleAnalyzer.cache)
                mat_types.MatModuleAnalyzer.cache.clear()
                # Sphinx < 9 caches docutils publishers bound to the main env.
                publishers = getattr(app.registry, "publishers", {})
                saved = dict(publishers)
                publishers.clear()
                app.env = app.builder.env = mat_types.MatObject.sphinx_env = worker
                try:
                    ret = func(arg)
                finally:
                    app.env = app.builder.env = mat_types.MatObject.sphinx_env = main
                    publishers.clear()
                    publishers.update(saved)
                    mat_types.MatModuleAnalyzer.cache.clear()
                    mat_types.MatModuleAnalyzer.cache.update(cache)
            if result_func:
                result_func(arg, ret)


PAGES = {
    "a.rst": "A\n=\n\n.. mat:autoscript:: Broken.m\n\n.. mat:autofunction:: used\n",
    "b.rst": "B\n=\n\n.. mat:autoclass:: pkg.Cls\n   :members:\n\n"
    ".. mat:autoscript:: Broken.m\n   :noindex:\n",
    "c.rst": "C\n=\n\n.. mat:autofolder:: src/lib/\n   :members:\n\n"
    "See :mat:func:`used`.\n",
    "d.rst": "D\n=\n\n.. mat:autofunction:: +pkg/other.m\n",
}
TOC = "Index\n=====\n\n.. toctree::\n\n   a\n   b\n   c\n   d\n"


def _outputs(app):
    html = {
        str(p.relative_to(app.outdir)): p.read_bytes()
        for p in sorted(app.outdir.glob("*.html"))
    }
    # A second app in one process re-registers nodes and directives.
    warnings = sorted(
        line
        for line in app.warning.getvalue().splitlines()
        if "WARNING" in line and "already registered" not in line
    )
    data = app.env.domaindata["mat"]
    return {
        "html": html,
        "inventory": (app.outdir / "objects.inv").read_bytes(),
        "warnings": warnings,
        "objects": data["objects"],
        "doc_sources": data["doc_sources"],
        "parsed": sorted(data["parse_cache"]),
    }


@pytest.fixture
def two_projects(tmp_path):
    for name in ("serial", "parallel"):
        write(tmp_path / name, {**FILES, **PAGES}, TOC)
        # Same sources (and mtimes) in both projects.
        for path in FILES:
            os.utime(tmp_path / name / path, ns=(10**18, 10**18))
    return tmp_path / "serial", tmp_path / "parallel"


def _normalize(outputs, root):
    text = str(root)
    outputs = dict(outputs)
    outputs["warnings"] = [w.replace(text, "<ROOT>") for w in outputs["warnings"]]
    outputs["doc_sources"] = {
        doc: {p.replace(text, "<ROOT>"): k for p, k in used.items()}
        for doc, used in outputs["doc_sources"].items()
    }
    outputs["parsed"] = [(p.replace(text, "<ROOT>"), *k) for p, *k in outputs["parsed"]]
    return outputs


def test_simulated_parallel_read_matches_serial(
    make_app, two_projects, monkeypatch, parsed
):
    serial_root, parallel_root = two_projects
    serial = make_app(srcdir=serial_root)
    serial.build()
    serial_parsed = len(parsed)

    monkeypatch.setattr(sphinx.builders, "parallel_available", True)
    monkeypatch.setattr(sphinx.builders, "ParallelTasks", ForkLikeTasks)
    parsed.clear()
    app = make_app(srcdir=parallel_root, parallel=4)
    ForkLikeTasks.app = app
    app.build()

    assert _normalize(_outputs(app), parallel_root) == _normalize(
        _outputs(serial), serial_root
    )
    # Each chunk parsed what its pages used; Broken.m warned once.
    assert len(parsed) >= serial_parsed
    assert app.warning.getvalue().count("may be invalid MATLAB") == 1

    # The merged parses serve the next build: nothing is parsed again.
    parsed.clear()
    for page in ("a.rst", "b.rst"):
        now = time.time_ns()
        os.utime(parallel_root / page, ns=(now, now))
    app2 = make_app(srcdir=parallel_root, parallel=4)
    ForkLikeTasks.app = app2
    app2.build()
    assert parsed == []
    assert app2.warning.getvalue().count("may be invalid MATLAB") == 1


@pytest.mark.parametrize("auto_link", [None, "all"])
def test_parallel_build_matches_serial(make_app, two_projects, auto_link):
    # Real -j where Sphinx can fork (POSIX); a serial fallback elsewhere.
    serial_root, parallel_root = two_projects
    conf = {"matlab_auto_link": auto_link}
    serial = make_app(srcdir=serial_root, confoverrides=conf)
    serial.build()
    app = make_app(srcdir=parallel_root, confoverrides=conf, parallel=4)
    app.build()
    assert _normalize(_outputs(app), parallel_root) == _normalize(
        _outputs(serial), serial_root
    )
    assert app.warning.getvalue().count("may be invalid MATLAB") == 1


def test_build_with_j_auto(tmp_path):
    write(tmp_path / "src", {**FILES, **PAGES}, TOC)
    out = {}
    for name, extra in (("serial", []), ("auto", ["-j", "auto"])):
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "sphinx",
                "-b",
                "html",
                "-q",
                *extra,
                str(tmp_path / "src"),
                str(tmp_path / name),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert proc.returncode == 0, proc.stderr
        out[name] = (
            sorted(proc.stderr.splitlines()),
            {p.name: p.read_bytes() for p in sorted((tmp_path / name).glob("*.html"))},
        )
    assert out["auto"] == out["serial"]
    assert sum("may be invalid MATLAB" in line for line in out["auto"][0]) == 1
