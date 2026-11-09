"""scmd quickstart: detection, the files it writes, the edits
outside the Sphinx source folder, the command line and the report
(plan.md Section 2.13, Phase 16).
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from sphinxcontrib import matlab_cli, matlab_quickstart
from sphinxcontrib.mat_types import IndexSettings, build_index
from sphinxcontrib.matlab_apidoc import main as apidoc_main
from sphinxcontrib.matlab_quickstart import _cli, _detect, _report, _write
from sphinxcontrib.matlab_quickstart._detect import Install

TESTS = Path(__file__).parent
QUICKSTART = TESTS / "roots" / "test_quickstart"
APIDOC = TESTS / "roots" / "test_apidoc_basics"
GOLDEN = TESTS / "quickstart_golden"
VERSION_INSTALL = Install("version", "sphinxcontrib-matlabdomain>=1.0")
ANSWERS = 'project = "Quickstart test"\nauthor = "Test Author"\n'
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false"]
HAS_GIT = shutil.which("git") is not None


# --- helpers -----------------------------------------------------------------


def copy_root(source, tmp_path, name="proj"):
    root = tmp_path / name
    shutil.copytree(source, root, ignore=shutil.ignore_patterns("conf.py"))
    return root


def git_init(root):
    subprocess.run([*GIT, "init", "-q"], cwd=root, check=True)
    subprocess.run([*GIT, "add", "-A"], cwd=root, check=True)
    subprocess.run([*GIT, "commit", "-qm", "init"], cwd=root, check=True)


def answers_file(tmp_path, text=ANSWERS):
    path = tmp_path / "answers.toml"
    path.write_text(text, encoding="utf-8")
    return str(path)


def tree(folder):
    """``{relative path: text}`` below ``folder``, line ends as LF, the
    copyright year as ``<YEAR>``.
    """
    out = {}
    for path in sorted(Path(folder).rglob("*")):
        if path.is_file() and "_build" not in path.parts:
            text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
            text = re.sub(r'copyright = "\d{4},', 'copyright = "<YEAR>,', text)
            out[path.relative_to(folder).as_posix()] = text
    return out


def golden_tree(name):
    return tree(GOLDEN / name / "docs")


def normalize(text, root):
    text = text.replace(str(root), "<ROOT>").replace("\r\n", "\n")
    return re.sub(r"\d+\.\d\d s\.", "<T> s.", text)


@pytest.fixture
def fixed(monkeypatch):
    """Fix the matlabdomain install, MyST importable, no git author."""
    monkeypatch.setattr(_detect, "matlabdomain_install", lambda: VERSION_INSTALL)
    monkeypatch.setattr(_detect, "is_importable", lambda _name: True)
    monkeypatch.setattr(_cli, "_git_author", lambda _root: "")


@pytest.fixture
def fake_uv(monkeypatch):
    """``uv`` on PATH; its commands are recorded, not run."""
    calls = []
    real_which, real_run = shutil.which, _write.run

    def which(name, *args, **kwargs):
        return "uv" if name == "uv" else real_which(name, *args, **kwargs)

    def run(command, cwd):
        if command[0] == "uv":
            calls.append(command)
            return 0, ""
        return real_run(command, cwd)

    monkeypatch.setattr(shutil, "which", which)
    monkeypatch.setattr(_write, "run", run)
    return calls


@pytest.fixture
def no_git(monkeypatch):
    monkeypatch.setattr(_write, "git_dirty", lambda _root: None)


@pytest.fixture
def replies(monkeypatch):
    """Answer ``input()`` from a list; record the prompts."""
    asked = []
    queue = []

    def fake_input(text):
        asked.append(text)
        if not queue:
            raise EOFError
        return queue.pop(0)

    monkeypatch.setattr("builtins.input", fake_input)
    return SimpleNamespace(asked=asked, queue=queue)


def run_uv_case(tmp_path):
    """Run the ``uv`` golden case: a git and uv project, ``-q`` with answers."""
    root = copy_root(QUICKSTART, tmp_path)
    (root / "pyproject.toml").write_text("[tool.uv]\npackage = false\n")
    git_init(root)
    status = matlab_cli.main(
        ["quickstart", str(root), "--quiet", "--answers", answers_file(tmp_path)]
    )
    return root, status


def run_plain_case(tmp_path):
    """Run the ``plain`` golden case: no git, folder grouping, pages not
    committed, no Markdown.
    """
    root = copy_root(APIDOC, tmp_path)
    text = (
        f'{ANSWERS}group = "folder"\napi_pages = "generate"\nmarkdown = false\n'
        'make = "plain"\n'
    )
    status = matlab_quickstart.main(
        [str(root), "-q", "--answers", answers_file(tmp_path, text)]
    )
    return root, status


# --- golden output -----------------------------------------------------------


@pytest.mark.skipif(not HAS_GIT, reason="needs git")
def test_golden_uv_project(tmp_path, capsys, fixed, fake_uv):
    root, status = run_uv_case(tmp_path)
    out = capsys.readouterr()
    assert status == 0, out.err
    assert normalize(out.out, root) == (GOLDEN / "uv" / "stdout.txt").read_text(
        encoding="utf-8"
    )
    assert tree(root / "docs") == golden_tree("uv")
    assert fake_uv == [
        [
            "uv",
            "add",
            "--frozen",
            "--group",
            "docs",
            "sphinx>=8.0",
            "sphinxcontrib-matlabdomain>=1.0",
            "myst-parser>=4,<6",
            "furo",
            "sphinx-autobuild",
        ]
    ]
    assert (root / ".gitignore").read_text() == "docs/_build/\n"
    assert (root / ".gitattributes").read_text() == "*.bat text eol=crlf\n"
    # make.bat has CRLF line ends, every other file LF
    for path in (root / "docs").rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            assert (b"\r\n" in data) == (path.name == "make.bat"), path
    # the generated conf.py gives the same API pages
    assert (
        matlab_cli.main(
            ["apidoc", "--quiet", "--check", "--conf-dir", str(root / "docs")]
        )
        == 0
    )
    assert "uv.lock" not in os.listdir(root)


@pytest.mark.skipif(not HAS_GIT, reason="needs git")
def test_uv_project_builds_without_warnings(tmp_path, make_app, fixed, fake_uv):
    pytest.importorskip("myst_parser")
    pytest.importorskip("furo")
    root, status = run_uv_case(tmp_path)
    assert status == 0
    app = make_app(
        srcdir=root / "docs", freshenv=True, confoverrides={"nitpicky": True}
    )
    app.build(force_all=True)
    assert app.warning.getvalue() == ""


def test_golden_plain_project(tmp_path, capsys, fixed, no_git):
    root, status = run_plain_case(tmp_path)
    out = capsys.readouterr()
    assert status == 0, out.err
    assert normalize(out.out, root) == (GOLDEN / "plain" / "stdout.txt").read_text(
        encoding="utf-8"
    )
    assert tree(root / "docs") == golden_tree("plain")
    # outside git it edits nothing outside the docs folder
    assert not (root / ".gitignore").exists()
    assert not (root / ".gitattributes").exists()
    assert apidoc_main(["-q", "--check", "-c", str(root / "docs")]) == 0


@pytest.mark.skipif(os.name != "nt", reason="Windows batch file")
def test_generated_batch_apidoc_check(tmp_path, fixed, no_git):
    root, status = run_plain_case(tmp_path)
    assert status == 0
    env = os.environ.copy()
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env["PATH"]
    result = subprocess.run(
        ["cmd.exe", "/c", "make.bat", "apidoc-check"],
        cwd=root / "docs",
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_golden_dry_run(tmp_path, capsys, fixed, no_git):
    root = copy_root(QUICKSTART, tmp_path)
    before = tree(root)
    status = matlab_quickstart.main(
        [str(root), "-q", "-n", "--answers", answers_file(tmp_path)]
    )
    out = capsys.readouterr()
    assert status == 0, out.err
    assert normalize(out.out, root) == (GOLDEN / "dry-run.txt").read_text(
        encoding="utf-8"
    )
    assert tree(root) == before


def test_simulink_project_gets_the_help_linker(tmp_path, capsys, fixed, no_git):
    root = copy_root(APIDOC, tmp_path)
    slx = TESTS / "simulink" / "fixtures" / "R2026b" / "slx"
    (root / "models" / "private").mkdir(parents=True)
    shutil.copyfile(slx / "probeModel.slx", root / "models" / "probeModel.slx")
    shutil.copyfile(slx / "probeLib.slx", root / "models" / "probeLib.slx")
    shutil.copyfile(slx / "probeRef.slx", root / "models" / "private" / "probeRef.slx")
    text = f'{ANSWERS}markdown = false\nmake = "plain"\nhtml_baseurl = "https://x.org/d/"\n'
    args = [str(root), "-q", "--answers", answers_file(tmp_path, text)]
    assert matlab_quickstart.main(args) == 0
    out = " ".join(normalize(capsys.readouterr().out, root).split())
    folder = root / "+sphinxcontrib" / "+matlabdomain"
    linker = folder / "simulinkDocumentationLinker.m"
    assert (
        linker.read_bytes()
        == (
            _write.MATLAB_TOOLS / "+sphinxcontrib" / "+matlabdomain" / linker.name
        ).read_bytes()
    )
    settings = json.loads((folder / "simulinkDocumentationLinker.json").read_text())
    assert settings == {
        "mode": "local",
        "local": "docs/_build/html/",
        "server": "http://127.0.0.1:8000/",
        "published": "https://x.org/d/",
    }
    assert (
        "Creating file +sphinxcontrib/+matlabdomain/simulinkDocumentationLinker.m "
        "(Help links of the Simulink files)." in out
    )
    assert "2 models, 1 library" in out
    assert "models/private/probeRef.slx" in out  # not callable
    conf = (root / "docs" / "conf.py").read_text(encoding="utf-8")
    assert (
        "    # The MATLAB function behind the Help links of the Simulink files.\n"
        '    "+sphinxcontrib/",\n'
    ) in conf

    # A second run keeps the settings and does not document the function.
    (folder / "simulinkDocumentationLinker.json").write_text('{"mode": "published"}')
    assert matlab_quickstart.main([*args, "--force"]) == 0
    out = capsys.readouterr().out
    assert (folder / "simulinkDocumentationLinker.json").read_text() == (
        '{"mode": "published"}'
    )
    assert "simulinkDocumentationLinker" not in out
    api = tree(root / "docs" / "API")
    assert not [name for name in api if "sphinxcontrib" in name]
    assert not [text for text in api.values() if "simulinkDocumentationLinker" in text]


def test_help_and_version(capsys):
    with pytest.raises(SystemExit):
        matlab_quickstart.main(["--version"])
    assert "scmd quickstart" in capsys.readouterr().out


# --- the Sphinx source folder ------------------------------------------------


def test_docs_must_be_inside_root(tmp_path, capsys):
    (tmp_path / "proj").mkdir()
    for docs in (tmp_path / "elsewhere", tmp_path / "proj"):
        status = matlab_quickstart.main([str(tmp_path / "proj"), "-q", "-o", str(docs)])
        assert status == 2
        assert "must be inside ROOT" in capsys.readouterr().err


def test_docs_on_another_drive(monkeypatch):
    def commonpath(paths):
        raise ValueError("another drive")

    monkeypatch.setattr(os.path, "commonpath", commonpath)
    assert not _cli._inside("D:\\docs", "C:\\proj")


def test_docs_in_use_quiet(tmp_path, capsys):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "mkdocs.md").write_text("x")
    assert matlab_quickstart.main([str(tmp_path), "-q"]) == 2
    err = capsys.readouterr().err
    assert "docs is in use: it has files but no conf.py" in err
    assert "-o" in err


def test_docs_in_use_asks_for_another(tmp_path, capsys, replies, fixed, no_git):
    root = copy_root(QUICKSTART, tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "index.md").write_text("# MkDocs\n")
    (root / "notes").write_text("a file named like a folder")
    replies.queue += ["", "notes", "sphinx", "n"]
    status = matlab_quickstart.main(
        [str(root), "-n", "--answers", answers_file(tmp_path, ANSWERS + _all_answers())]
    )
    out = capsys.readouterr().out
    assert status == 0
    assert "docs is in use: it has files but no conf.py." in out
    assert "notes is in use" in out
    assert "Would create file sphinx/conf.py." in out
    # no suggestion: the prompt has no default
    assert replies.asked[0] == "> Sphinx source folder, relative to ROOT: "


def test_empty_docs_folder_is_used(tmp_path, capsys, fixed, no_git):
    root = copy_root(QUICKSTART, tmp_path)
    (root / "docs").mkdir()
    assert matlab_quickstart.main([str(root), "-q", "-n"]) == 0
    assert "Would create file docs/conf.py." in capsys.readouterr().out


def test_existing_conf_py_stops(tmp_path, capsys, fixed, no_git):
    root = copy_root(QUICKSTART, tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "conf.py").write_text("# mine\n")
    assert matlab_quickstart.main([str(root), "-q"]) == 2
    assert "docs/conf.py exists" in capsys.readouterr().err
    assert (root / "docs" / "conf.py").read_text() == "# mine\n"


def test_force_rewrites_its_files(tmp_path, capsys, fixed, no_git):
    root = copy_root(QUICKSTART, tmp_path)
    args = [str(root), "-q", "--answers", answers_file(tmp_path)]
    assert matlab_quickstart.main(args) == 0
    (root / "docs" / "conf.py").write_text("# mine\n")
    (root / "docs" / "notes.rst").write_text("Notes\n=====\n")
    capsys.readouterr()
    assert matlab_quickstart.main([*args, "--force"]) == 0
    out = capsys.readouterr().out
    assert "Updating file docs/conf.py." in out
    assert "Creating file" not in out
    assert "API page" not in out.split("Project:")[0]
    assert (root / "docs" / "notes.rst").read_text() == "Notes\n=====\n"


# --- git and the edits outside the Sphinx source folder ---------------------


@pytest.mark.skipif(not HAS_GIT, reason="needs git")
@pytest.mark.parametrize("name", ["pyproject.toml", ".gitignore", ".gitattributes"])
def test_uncommitted_changes_stop(tmp_path, capsys, fixed, name):
    root = copy_root(QUICKSTART, tmp_path)
    git_init(root)
    (root / name).write_text("x = 1\n")
    assert matlab_quickstart.main([str(root), "-q"]) == 2
    err = capsys.readouterr().err
    assert f"{name} has uncommitted changes" in err
    assert not (root / "docs").exists()
    # a dry run says so and goes on
    assert matlab_quickstart.main([str(root), "-q", "-n"]) == 0
    assert f"Would stop: {name} has uncommitted" in capsys.readouterr().out


@pytest.mark.skipif(not HAS_GIT, reason="needs git")
def test_primer_git_checkpoint(tmp_path, fixed, fake_uv):
    root = copy_root(QUICKSTART, tmp_path)
    git_init(root)
    (root / "pyproject.toml").write_text("[tool.uv]\npackage = false\n")
    (root / "uv.lock").write_text("version = 1\n")
    assert _write.git_dirty(root) == ["pyproject.toml"]
    subprocess.run(
        [*GIT, "add", "--", "pyproject.toml", "uv.lock"], cwd=root, check=True
    )
    subprocess.run(
        [*GIT, "commit", "-qm", "Prepare Python documentation tools"],
        cwd=root,
        check=True,
    )
    assert _write.git_dirty(root) == []
    assert matlab_quickstart.main([str(root), "--quiet"]) == 0
    assert (root / "docs" / "conf.py").is_file()


@pytest.mark.skipif(not HAS_GIT, reason="needs git")
def test_git_edits_keep_line_ends_and_skip_present_lines(tmp_path, capsys, fixed):
    root = copy_root(QUICKSTART, tmp_path)
    (root / ".gitignore").write_bytes(b"*.asv\r\ndocs/_build/")
    (root / ".gitattributes").write_bytes(b"*.bat text eol=crlf\n")
    git_init(root)
    text = ANSWERS + 'api_pages = "generate"\n'
    assert (
        matlab_quickstart.main(
            [str(root), "-q", "--answers", answers_file(tmp_path, text)]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert (
        root / ".gitignore"
    ).read_bytes() == b"*.asv\r\ndocs/_build/\r\ndocs/API/\r\n"
    assert (root / ".gitattributes").read_bytes() == b"*.bat text eol=crlf\n"
    assert "Adding to .gitignore: docs/API/" in out
    assert ".gitattributes" not in out
    # not a uv project: the dependencies are printed
    assert "Install the docs dependencies:" in out


def test_not_in_git_prints_the_lines(tmp_path, capsys, fixed, no_git):
    root = copy_root(QUICKSTART, tmp_path)
    assert matlab_quickstart.main([str(root), "-q"]) == 0
    out = capsys.readouterr().out
    assert "Not in a git repository; add to .gitignore: docs/_build/" in out
    assert not (root / ".gitignore").exists()


def test_uv_add_failure(tmp_path, capsys, fixed, monkeypatch):
    root = copy_root(QUICKSTART, tmp_path)
    (root / "uv.lock").write_text("")
    monkeypatch.setattr(_write, "git_dirty", lambda _root: [])
    monkeypatch.setattr(shutil, "which", lambda name, *_a, **_k: name)
    monkeypatch.setattr(_write, "run", lambda _command, _cwd: (2, "no pyproject.toml"))
    assert matlab_quickstart.main([str(root), "-q"]) == 1
    err = capsys.readouterr().err
    assert "uv add --frozen --group docs" in err
    assert "no pyproject.toml" in err
    assert not (root / "docs").exists()


@pytest.mark.parametrize(
    ("dry_run", "in_git", "uv_found", "header"),
    [
        (True, True, True, "Would run:"),
        (False, False, True, "Not in a git repository; run:"),
        (False, True, False, "uv was not found; run:"),
    ],
)
def test_uv_commands_printed(monkeypatch, dry_run, in_git, uv_found, header):
    monkeypatch.setattr(shutil, "which", lambda name: name if uv_found else None)
    answers = {"markdown": False, "theme": "alabaster", "make": "uv"}
    facts = {"install": VERSION_INSTALL, "uv": "uv.lock", "pyproject": True}
    args = SimpleNamespace(dry_run=dry_run)
    commands, shown, lines = _cli._dependencies(answers, facts, args, in_git)
    assert commands == []
    assert shown == header
    assert lines == [
        'uv add --frozen --group docs "sphinx>=8.0" '
        '"sphinxcontrib-matlabdomain>=1.0" sphinx-autobuild'
    ]


@pytest.mark.parametrize(
    ("pyproject", "first"), [(False, "uv init --bare"), (True, "uv add")]
)
def test_uv_make_files_without_a_uv_project(pyproject, first):
    answers = {"markdown": False, "theme": "furo", "make": "uv"}
    facts = {"install": VERSION_INSTALL, "uv": None, "pyproject": pyproject}
    args = SimpleNamespace(dry_run=False)
    commands, header, lines = _cli._dependencies(answers, facts, args, True)
    assert commands == []
    assert header == "Install the docs dependencies:"
    assert lines[0].startswith(first)


def test_install_lines():
    answers = {"markdown": True, "theme": "sphinx_rtd_theme"}
    editable = Install("editable", "/src/matlab domain")
    assert _write.install_lines(answers, editable, False) == [
        'pip install "sphinx>=8.0" "myst-parser>=4,<6" sphinx-rtd-theme '
        "sphinx-autobuild",
        'pip install -e "/src/matlab domain"',
    ]
    lines = _write.install_lines(answers, VERSION_INSTALL, True)
    assert lines[0].startswith("Add to pyproject.toml")
    assert '      "sphinxcontrib-matlabdomain>=1.0",' in lines
    assert lines[-1].startswith("  pip install")
    assert _write.uv_commands(answers, editable)[1] == [
        "uv",
        "add",
        "--frozen",
        "--group",
        "docs",
        "--editable",
        "/src/matlab domain",
    ]


def test_guide_install_drops_a_local_folder():
    facts = {"install": Install("editable", "/src")}
    assert _cli._guide_install(facts).requirement == "sphinxcontrib-matlabdomain"
    facts = {"install": VERSION_INSTALL}
    assert _cli._guide_install(facts) is VERSION_INSTALL


@pytest.mark.skipif(not HAS_GIT, reason="needs git")
def test_git_dirty(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.m").write_text("x = 1;\n")
    git_init(root)
    assert _write.git_dirty(root) == []
    (root / ".gitignore").write_text("x\n")
    (root / "pyproject.toml").write_text("")
    assert _write.git_dirty(root) == [".gitignore", "pyproject.toml"]
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    assert _write.git_dirty(root) is None


def test_git_dirty_outside_a_work_tree(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: name)
    monkeypatch.setattr(
        _write, "run", lambda _command, _cwd: (128, "not a git repository")
    )
    assert _write.git_dirty(tmp_path) is None


def test_git_author(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    assert _cli._git_author(tmp_path) == ""
    monkeypatch.setattr(shutil, "which", lambda name: name)
    monkeypatch.setattr(_write, "run", lambda _command, _cwd: (1, ""))
    assert _cli._git_author(tmp_path) == ""
    monkeypatch.setattr(_write, "run", lambda _command, _cwd: (0, "Ada"))
    assert _cli._git_author(tmp_path) == "Ada"


def test_run_runs_a_command(tmp_path):
    status, output = _write.run([sys.executable, "-c", "print('hi')"], tmp_path)
    assert (status, output) == (0, "hi")


def test_append_and_missing_lines(tmp_path):
    path = tmp_path / ".gitignore"
    assert _write.missing_lines(path, ["a"]) == ["a"]
    _write.append_lines(path, ["a"])
    assert path.read_bytes() == b"a\n"
    path.write_bytes(b"a")
    _write.append_lines(path, ["b"])
    assert path.read_bytes() == b"a\nb\n"
    assert _write.missing_lines(path, ["a", " b ", "c"]) == [" b ", "c"]


def test_write_files(tmp_path):
    files = {"a.txt": b"a", "sub/b.txt": b"b"}
    written = _write.write_files(tmp_path, files, dry_run=True)
    assert written.created == ["a.txt", "sub/b.txt"]
    assert not (tmp_path / "a.txt").exists()
    _write.write_files(tmp_path, files, dry_run=False)
    written = _write.write_files(tmp_path, {**files, "a.txt": b"A"}, dry_run=False)
    assert (written.updated, written.unchanged) == (["a.txt"], ["sub/b.txt"])
    assert (tmp_path / "a.txt").read_bytes() == b"A"


def test_py_literals():
    assert _write.py('a"b') == '"a\\"b"'
    assert _write.py(("Inputs", "params_style")) == '("Inputs", "params_style")'
    assert _write.headings_text(["Description", ("Inputs", "params_style")]) == (
        "`Description:`, `Inputs:`"
    )


# --- detection ---------------------------------------------------------------


class FakeDist:
    def __init__(self, files, version="1.2.dev3+gabc"):
        self.files = files
        self.version = version

    def read_text(self, name):
        return self.files.get(name)


@pytest.mark.parametrize(
    ("direct_url", "kind", "requirement"),
    [
        (None, "version", "sphinxcontrib-matlabdomain>=1.2.dev3"),
        (
            {
                "url": "https://github.com/o/r",
                "vcs_info": {"vcs": "git", "commit_id": "abc123"},
            },
            "vcs",
            "sphinxcontrib-matlabdomain @ git+https://github.com/o/r@abc123",
        ),
        (
            {"url": "https://example.org/x.whl", "archive_info": {}},
            "url",
            "sphinxcontrib-matlabdomain @ https://example.org/x.whl",
        ),
        (
            {"url": "file:///tmp/src", "dir_info": {}},
            "url",
            "sphinxcontrib-matlabdomain @ file:///tmp/src",
        ),
    ],
)
def test_matlabdomain_install(direct_url, kind, requirement):
    files = {} if direct_url is None else {"direct_url.json": json.dumps(direct_url)}
    install = _detect.matlabdomain_install(FakeDist(files))
    assert (install.kind, install.requirement) == (kind, requirement)


def test_matlabdomain_install_editable():
    url = Path(__file__).parent.as_uri()
    files = {
        "direct_url.json": json.dumps({"url": url, "dir_info": {"editable": True}})
    }
    install = _detect.matlabdomain_install(FakeDist(files))
    assert install.kind == "editable"
    assert Path(install.requirement) == Path(__file__).parent


def test_matlabdomain_distribution(monkeypatch):
    egg = FakeDist({})
    installed = FakeDist({"INSTALLER": "uv"})
    monkeypatch.setattr(
        _detect.metadata, "distributions", lambda **_kw: [egg, installed]
    )
    assert _detect._distribution() is installed
    monkeypatch.setattr(_detect.metadata, "distributions", lambda **_kw: [egg])
    assert _detect._distribution() is egg
    monkeypatch.setattr(_detect.metadata, "distributions", lambda **_kw: [])
    assert _detect.matlabdomain_install() == Install(
        "version", "sphinxcontrib-matlabdomain"
    )


def test_uv_project(tmp_path):
    assert _detect.uv_project(tmp_path) is None
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")
    assert _detect.uv_project(tmp_path) is None
    (tmp_path / "pyproject.toml").write_text("[tool.uv]\n")
    assert _detect.uv_project(tmp_path) == "[tool.uv]"
    (tmp_path / "uv.lock").write_text("")
    assert _detect.uv_project(tmp_path) == "uv.lock"
    (tmp_path / "pyproject.toml").write_text("[tool")
    assert _detect.read_pyproject(tmp_path) is None


def test_matlab_versions(tmp_path):
    (tmp_path / "Jenkinsfile").write_text("matlab r2025A\nR2025a")
    (tmp_path / "readme.txt").write_text("R2024b")
    (tmp_path / "README.d").mkdir()
    found = _detect.matlab_versions(tmp_path)
    assert found == {"R2025a": {"Jenkinsfile": 2}, "R2024b": {"readme.txt": 1}}
    assert _detect.most_frequent_release(found) == "R2025a"
    tie = {"R2024b": {"a": 1}, "R2025a": {"b": 1}}
    assert _detect.most_frequent_release(tie) == "R2025a"
    assert _detect.matlab_version_default(found) == ("R2025a", None)
    assert _detect.matlab_version_default({}) == (
        "R2026a",
        "the default; none is named",
    )
    assert _detect.matlab_version_default({"R2019b": {"a": 1}}) == (
        "R2024a",
        "the oldest supported release; R2019b is named",
    )


def test_submodule_paths(tmp_path):
    assert _detect.submodule_paths(tmp_path) == []
    gitmodules = tmp_path / ".gitmodules"
    gitmodules.write_text(
        '[submodule "a"]\n\tpath = ext/a\n[submodule "b"]\n\turl = x\n'
    )
    assert _detect.submodule_paths(tmp_path) == ["ext/a"]
    gitmodules.write_text("path = no section\n")
    assert _detect.submodule_paths(tmp_path) == []
    gitmodules.write_bytes(b'[submodule "\xff"]\n')
    assert _detect.submodule_paths(tmp_path) == []


def test_project_path_toml(tmp_path):
    assert _detect.project_path(tmp_path) is None
    toml = tmp_path / "matlab.toml"
    toml.write_text(
        '[folders]\npath = ["./src/", "..\\\\other", "C:/abs", "tools\\\\x"]\n'
        '[project]\nstartup-files = ["src/up.m"]\nshutdown-files = ["../down.m"]\n'
    )
    path = _detect.project_path(tmp_path)
    assert path == _detect.ProjectPath(
        "matlab.toml", frozenset({"src", "tools/x"}), ("src/up.m",)
    )
    toml.write_text('name = "x"\n')
    assert _detect.project_path(tmp_path) is None
    toml.write_text("[x")
    assert _detect.project_path(tmp_path) is None
    # wrong types are skipped, not a crash
    toml.write_text('folders = "src"\nproject = 1\n')
    assert _detect.project_path(tmp_path) is None
    toml.write_text('[folders]\npath = ["src", 1]\n[project]\nstartup-files = "up.m"\n')
    assert _detect.project_path(tmp_path) == _detect.ProjectPath(
        "matlab.toml", frozenset({"src"}), ()
    )


def test_project_path_unreadable_toml(tmp_path, monkeypatch):
    (tmp_path / "matlab.toml").write_text("[folders]\npath = ['src']\n")

    def denied(_root):
        raise PermissionError(13, "denied")

    monkeypatch.setattr(_detect, "_project_toml", denied)
    assert _detect.project_path(tmp_path) is None


# What MATLAB R2026a writes for path folders src and src/sub, a start-up and a
# shut-down file, and a referenced project: one <Info> per file in the
# multi-file and fixed-path multi-file layouts, all in Project.xml otherwise.
PRJ_FILES = {
    "EEtU/YBxV.xml": '<?xml version="1.0"?>\n<Info Ref="src" Type="Relative"/>\n',
    "EEtU/5sL8.xml": '<?xml version="1.0"?>\n<Info Ref="src/sub" Type="Relative"/>\n',
    "EEtU/5sL8p.xml": '<?xml version="1.0"?>\n<Info location="5f" type="Reference"/>\n',
    "KAXf/RAd2.xml": '<?xml version="1.0"?>\n<Info File="src/up.m" '
    'GroupUUID="default" Icon="" Name="up" Type="StartUp" Visible="0"/>\n',
    "KAXf/6Ypu.xml": '<?xml version="1.0"?>\n<Info File="src/down.m" '
    'GroupUUID="default" Icon="" Name="down" Type="Shutdown" Visible="0"/>\n',
    "U54h/U54h.xml": '<?xml version="1.0"?>\n<Info Ref="../Other" Type="Relative"/>\n',
}


@pytest.mark.parametrize("layout", ["multi-file", "single file"])
def test_project_path_prj_layouts(tmp_path, layout):
    folder = tmp_path / "resources" / "project"
    if layout == "single file":
        folder.mkdir(parents=True)
        body = "".join(text.split("?>")[-1] for text in PRJ_FILES.values())
        (folder / "Project.xml").write_text(
            f'<project MetadataType="monolithic">{body}</project>\n'
        )
    else:
        for name, text in PRJ_FILES.items():
            (folder / name).parent.mkdir(parents=True, exist_ok=True)
            (folder / name).write_text(text)
    # a folder named like an XML file cannot be read: skipped
    (folder / "odd.xml").mkdir()
    path = _detect.project_path(tmp_path)
    assert path is not None
    assert path.folders == {"src", "src/sub"}
    assert sorted(path.hooks) == ["src/down.m", "src/up.m"]
    refs = {"src/f.m", "src/sub/g.m", "data/d.m", "src/up.m", "src/down.m"}
    assert _detect.path_suggestions(refs, path) == ["data", "src/down.m", "src/up.m"]


def test_project_path_prj(tmp_path):
    xml = tmp_path / "resources" / "project" / "Root.type.ProjectPath" / "1.xml"
    xml.parent.mkdir(parents=True)
    xml.write_text(
        '<Info Ref="" Type="Relative"/>\n<Info Ref="src" Type="Relative"/>\n'
        '<Info File="startup.m" Name="s" Type="StartUp"/>\n'
        '<Info File="bye.m" Type="Shutdown">\n<Info Type="Relative"/>\n<Info/>\n'
    )
    path = _detect.project_path(tmp_path)
    assert path == _detect.ProjectPath(
        "resources/project", frozenset({"", "src"}), ("startup.m", "bye.m")
    )


def test_path_suggestions():
    path = _detect.ProjectPath("matlab.toml", frozenset({"src", "lib/a/b"}), ("up.m",))
    refs = {
        "src/f.m",  # on the path
        "src/+pkg/g.m",  # in a namespace on the path
        "data/x/d.m",  # not on the path
        "lib/a/old/o.m",  # lib/a holds a path folder
        "lib/a/b/c/n.m",  # every level holds a path folder or is one: none
        "up.m",  # a hook at the root (the root is not on the path)
        "+top/t.m",  # a namespace at the root
    }
    assert _detect.path_suggestions(refs, path) == [
        "+top",
        "data",
        "lib/a/b/c",
        "lib/a/old",
        "up.m",
    ]
    rooted = _detect.ProjectPath("x", frozenset({"", "lib"}), ())
    assert _detect.path_suggestions({"f.m", "lib/sub/g.m"}, rooted) == ["lib/sub"]
    nested = _detect.ProjectPath("x", frozenset({"a/b/c"}), ())
    assert _detect.path_suggestions({"a/b/f.m"}, nested) == []


def test_code_next_to(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "f.m").write_text("")
    (tmp_path / "a" / "n.md").write_text("")
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "n.md").write_text("")
    paths = [str(tmp_path / "a" / "n.md"), str(tmp_path / "b" / "n.md")]
    assert _detect.code_next_to(paths) == paths[:1]


def test_is_importable():
    assert _detect.is_importable("json")
    assert not _detect.is_importable("no_such_module_here")


def test_help_blocks():
    lines = [
        "% header",  # first block
        "",
        "x = 1;",
        "% a code comment",  # not help
        "y = 2;",
        "% before",  # before a function
        "function f",
        "",
        "% after",  # after a function, past a blank line
    ]
    blocks = _detect.help_blocks(lines)
    assert [[line for _, line in block] for block in blocks] == [
        ["% header"],
        ["% before"],
        ["% after"],
    ]


def survey_of(tmp_path, files):
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return _detect.survey(build_index(IndexSettings(str(tmp_path))))


def test_survey_and_headings(tmp_path):
    files = {}
    for i in range(12):
        heading = "Inputs" if i < 10 else "Input"
        files[f"f{i}.m"] = (
            f"function f{i}\n% F{i} help.\n% {heading}:\n%   x: a\n% Returns:\n"
            "%   y\n% Name-Value Pairs:\n% Option:\n"
        )
    for i in range(11):
        files[f"o{i}.m"] = f"function o{i}\n% O{i} help.\n% option:\n%   x\n"
    files["legal.m"] = "% LEGAL help.\n% (c) Copyright 2026\nx = 1;\n"
    files["late.m"] = "x = 1;\n% Copyright 2026, a code comment\n"
    found = survey_of(tmp_path, files)
    assert found.legal == ["legal.m:2"]
    headings = _detect.napoleon_headings(found)
    # One heading, case folded: Option in 12 files and option in 11.
    assert headings.entries == [
        ("Option", "params_style"),
        ("Inputs", "params_style"),
        ("Input", "Inputs"),
    ]
    assert headings.used == [("Option", 23), ("Inputs", 10), ("Input", 2)]
    assert headings.builtin == [("Returns", 12)]
    assert headings.unmatchable == [("Name-Value Pairs", 12)]
    assert headings.unused == []
    rare = _detect.napoleon_headings(found, threshold=100)
    assert rare.entries == []
    assert rare.unused == [("Option", 23), ("Inputs", 10), ("Input", 2)]


def test_headings_unused_skips_prose():
    found = _detect.Survey(
        spellings={
            "desirable properties of x": {"Desirable properties of X": 1},
            "inputs and outputs": {"Inputs and outputs": 1},
            "name-value arguments": {"Name-Value Arguments": 1},
            "see it": {"See it": 1},
            "algorithm": {"Algorithm": 1},
        },
        files={
            "desirable properties of x": {1},
            "inputs and outputs": {1},
            "name-value arguments": {1},
            "see it": {1},
            "algorithm": {1},
        },
        legal=[],
    )
    headings = _detect.napoleon_headings(found)
    assert headings.unused == [
        ("Algorithm", 1),
        ("Inputs and outputs", 1),
    ]


def test_headings_singular_section_plural_alias():
    found = _detect.Survey(
        spellings={
            "note x": {"Note x": 12},
            "note xs": {"Note xs": 3},
            "rare": {"Rare": 1},
        },
        files={"note x": set(range(12)), "note xs": {1, 2, 3}, "rare": {1}},
        legal=[],
    )
    headings = _detect.napoleon_headings(found)
    assert headings.entries == ["Note x", ("Note xs", "Note x")]
    assert headings.unused == [("Rare", 1)]


def test_survey_skips_files_without_text(tmp_path):
    (tmp_path / "f.m").write_text("function f\n% Inputs:\nend\n")
    index = build_index(IndexSettings(str(tmp_path)))
    index.text_cache.clear()
    assert _detect.survey(index).files == {}


def test_inventory(tmp_path):
    files = {
        "+a/+b/f.m": "function f\nend\n",
        "+a/plain/g.m": "function g\nend\n",
        "+a/@C/C.m": "classdef C\nend\n",
        "bad-name.m": "x = 1;\n",
        "private/bad-name2.m": "x = 1;\n",
        "Contents.m": "% help\n",
        "sub/Contents.m": "% help\n",
        "latin.m": "% caf\xe9\n",
        "one/h.m": "function h\nend\n",
        "two/h.m": "function h\nend\n",
    }
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("latin-1"))
    index = build_index(IndexSettings(str(tmp_path)))
    found = _detect.inventory(index)
    assert found["namespaces"] == ["a", "a.b"]
    assert found["not_callable"] == ["bad-name.m"]
    assert found["encoding"] == ["latin.m"]
    assert found["duplicates"] == {"h": ["one/h.m", "two/h.m"]}
    assert found["unknown"] == 0


# --- answers and prompts -----------------------------------------------------


def _all_answers():
    return (
        'matlab_version = "R2024b"\ngroup = "namespace"\ntheme = "furo"\n'
        'html_baseurl = ""\nexclude = []\nmarkdown = true\nsidecars = true\n'
        'make = "plain"\nguide = true\napi_pages = "commit"\n'
        "napoleon_custom_sections = []\n"
    )


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[x", "Expected"),
        ("color = 1\n", "unknown keys color"),
        ("markdown = 1\n", "markdown must be true or false"),
        ('group = "flat"\n', "group must be 'namespace' or 'folder'"),
        ('exclude = ["a\\\\b"]\n', "must use '/'"),
        ("napoleon_custom_sections = 1\n", "must be a list"),
        ("napoleon_custom_sections = [[1, 2]]\n", "[heading, style] pairs"),
        ('project = " "\n', "project must be a text"),
        ("html_baseurl = 1\n", "html_baseurl must be a text"),
        ('matlab_version = "R2019b"\n', "older than the oldest supported"),
    ],
)
def test_bad_answers(tmp_path, capsys, text, message):
    status = matlab_quickstart.main(
        [str(tmp_path), "--answers", answers_file(tmp_path, text)]
    )
    assert status == 2
    assert message in capsys.readouterr().err


def test_missing_answers_file(tmp_path, capsys):
    status = matlab_quickstart.main(
        [str(tmp_path), "--answers", str(tmp_path / "no.toml")]
    )
    assert status == 2
    assert "--answers" in capsys.readouterr().err


def test_answers_round_trip(tmp_path):
    answers = _cli.read_answers(answers_file(tmp_path, ANSWERS + _all_answers()))
    answers["napoleon_custom_sections"] = ["Description", ("Inputs", "params_style")]
    answers["exclude"] = ["tests"]
    path = tmp_path / "saved.toml"
    path.write_text(_cli.dumps(answers), encoding="utf-8")
    assert _cli.read_answers(path) == answers
    assert 'exclude = [\n    "tests",\n]' in path.read_text()


def test_sidecars_need_markdown(tmp_path, capsys, fixed, no_git):
    root = copy_root(QUICKSTART, tmp_path)
    text = ANSWERS + "markdown = false\nsidecars = true\n"
    assert (
        matlab_quickstart.main(
            [str(root), "-q", "--answers", answers_file(tmp_path, text)]
        )
        == 2
    )
    assert "sidecars = true needs markdown = true" in capsys.readouterr().err


def test_prompts(tmp_path, capsys, replies, fixed, no_git):
    root = copy_root(QUICKSTART, tmp_path)
    replies.queue += [
        "",  # project: the folder name
        "Ada",  # author
        "2025b",  # not a release: asked again
        "R2025b",
        "flat",  # a bad grouping
        "folder",
        "",  # theme
        "ftp://x",  # not a web address: asked again
        "https://example.org/docs/",  # published site
        "data, ext",  # exclusions
        "maybe",  # not y or n
        "y",  # markdown
        "n",  # sidecars
        "",  # make files
        "n",  # guide
        "generate",  # API pages
        "n",  # napoleon sections
        "",  # save the answers: yes in a dry run
        str(tmp_path / "saved.toml"),
    ]
    assert matlab_quickstart.main([str(root), "-n"]) == 0
    out = capsys.readouterr().out
    assert "* matlab_version must look like" in out
    assert "* Answer y or n." in out
    assert "Help headings in 10 or more files, and their variants:" in out
    assert replies.asked[0] == "> Project name [proj]: "
    assert replies.asked[1] == "> Author names [The proj authors]: "
    saved = _cli.read_answers(tmp_path / "saved.toml")
    assert saved["exclude"] == ["data", "ext"]
    assert saved["napoleon_custom_sections"] == []
    assert saved["matlab_version"] == "R2025b"
    assert saved["html_baseurl"] == "https://example.org/docs/"
    assert "* html_baseurl must start with https:// or http://" in out
    assert "Saved the answers" in out
    assert not (root / "docs").exists()


def test_save_answers_default_file(tmp_path, capsys, replies, fixed, no_git):
    root = copy_root(QUICKSTART, tmp_path)
    args = [str(root), "-q", "--answers", answers_file(tmp_path)]
    # -q asks nothing, also not to save
    assert matlab_quickstart.main(args) == 0
    assert replies.asked == []
    namespace = SimpleNamespace(dry_run=False, answers=None)
    answers = _cli.read_answers(answers_file(tmp_path, ANSWERS + _all_answers()))
    replies.queue += ["y", ""]
    _cli.save_answers(namespace, str(root), answers)
    assert _cli.read_answers(root / _cli.ANSWERS_FILE) == answers
    replies.queue += [""]
    _cli.save_answers(namespace, str(root), {})
    assert replies.asked[-1] == "> Save the answers to a file [y/N]: "


def test_interrupted(tmp_path, capsys, replies, fixed, no_git):
    root = copy_root(QUICKSTART, tmp_path)
    assert matlab_quickstart.main([str(root)]) == 1
    assert "[Interrupted.]" in capsys.readouterr().out


def test_napoleon_prompt_skipped_without_headings(tmp_path):
    prompter = _cli.Prompter({}, quiet=False)
    _cli._ask_napoleon(prompter, _detect.Headings([], [], [], [], []))
    assert prompter.answers == {"napoleon_custom_sections": []}


def test_shown_defaults():
    assert _cli._shown(True) == "Y/n"
    assert _cli._shown(False) == "y/N"
    assert _cli._shown([]) == "none"
    assert _cli._shown(["a", "b"]) == "a, b"
    assert _cli._shown("x") == "x"
    assert _cli.patterns(" a, ,b ") == ["a", "b"]


# --- the report --------------------------------------------------------------


def test_report_lists(capsys):
    assert _report._count(1, "class") == "1 class"
    assert _report._count(2, "class") == "2 classes"
    assert _report._items([str(i) for i in range(12)]).endswith("9, and 2 more")


def record(ref, kind="function", name: str | None = "x", warnings=()):
    return {
        "reference": ref,
        "type": kind,
        "matlab_name": name,
        "private": False,
        "warnings": list(warnings),
    }


def test_report_inventory_details(capsys):
    records = [record("x.mlapp", "unknown")]
    records.append(record("bad-name.m", "script", None, [("encoding", "", None)]))
    names = {f"d{i}": [f"a/d{i}.m", f"b/d{i}.m"] for i in range(12)}
    index = SimpleNamespace(
        index={r["reference"]: r for r in records},
        matlab_names=names,
        sidecars={"a/n.md": {}},
    )
    _report._inventory(index)
    out = capsys.readouterr().out
    assert "1 unreadable" in out
    assert "1 sidecar doc" in out
    assert "and 2 more" in out
    assert "Not callable (1" in out
    assert "Not UTF-8 (1" in out


def test_report_empty_project(tmp_path, capsys):
    index = build_index(IndexSettings(str(tmp_path)))
    _report._inventory(index)
    _report._headings(_detect.Headings([], [], [], [], []), _detect.Survey({}, {}, []))
    out = capsys.readouterr().out
    assert "0 files indexed; 0 namespaces" in out
    assert "Help headings:\n  none" in out


def test_report_facts_variants(capsys):
    facts = {
        "versions": {},
        "version": "R2026a",
        "version_note": "the default; none is named",
        "uv": None,
        "install": VERSION_INSTALL,
        "submodules": [],
        "path": _detect.ProjectPath("matlab.toml", frozenset({"src"}), ()),
    }
    answers = {"matlab_version": "R2025a", "markdown": False}
    _report._facts(answers, facts, [], [])
    out = capsys.readouterr().out
    assert "matlab_version: R2025a\n" in out
    assert "Not on it" not in out
    assert "Sidecar docs" not in out
    _report._facts(answers, {**facts, "path": None}, [], [])
    assert "MATLAB project path: none read" in capsys.readouterr().out


def test_report_next_steps(capsys):
    answers = {"make": "plain", "api_pages": "generate"}
    _report._next_steps(answers, "doc", dry_run=False, installed=False, uv=None)
    out = capsys.readouterr().out
    assert "Install the docs dependencies (above)." in out
    assert "apidoc-check" not in out
    answers = {"make": "plain", "api_pages": "commit"}
    _report._next_steps(answers, "doc", dry_run=False, installed=True, uv="uv.lock")
    out = capsys.readouterr().out
    assert "Lock and install the docs dependencies:" in out
