"""scmd skills: the agent skills in the package, listing and installing them."""

import importlib.util
import os
from pathlib import Path

import pytest

from sphinxcontrib.matlab_skills import _cli, main

PACKAGE = Path(_cli.__file__).parent
NAMES = ["migrating-from-0x", "setting-up-a-project"]


def files(root):
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )


def test_skills_in_the_package():
    found = _cli.skills()
    assert list(found) == NAMES
    for name, description in found.items():
        header = _cli._front_matter((PACKAGE / name / "SKILL.md").read_text("utf-8"))
        # Agent tools load a skill only when its name is its folder's name.
        assert header["name"] == name
        assert 0 < len(description) <= 1024


def test_skills_are_self_contained():
    """A skill uses only its own scripts: each one can be installed alone.
    Shared scripts are copies and stay identical.
    """
    for name in NAMES:
        text = (PACKAGE / name / "SKILL.md").read_text("utf-8")
        for other in NAMES:
            if other != name:
                assert f"{other}/scripts/" not in text
    shared = "scripts/group_warnings.py"
    copies = {(PACKAGE / name / shared).read_bytes() for name in NAMES}
    assert len(copies) == 1


def test_front_matter():
    text = "---\nname: a\nno colon\ndescription: x: y\n---\nbody: no\n"
    assert _cli._front_matter(text) == {"name": "a", "description": "x: y"}
    assert _cli._front_matter("name: a\n") == {}
    assert _cli._front_matter("---\nname: a\n") == {"name": "a"}
    assert _cli._front_matter("") == {}


def test_list(capsys):
    assert main(["list"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [line for line in lines if not line.startswith(" ")] == NAMES
    assert all(len(line) <= 79 for line in lines)


def test_install_all_into_the_default_folder(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["install"]) == 0
    dest = tmp_path / ".github" / "skills"
    assert sorted(os.listdir(dest)) == NAMES
    for name in NAMES:
        assert files(dest / name) == files(PACKAGE / name)
    out = capsys.readouterr().out
    assert (
        f"Installed migrating-from-0x in {Path('.github/skills/migrating-from-0x')}."
        in out
    )


def test_install_named_skills(tmp_path, capsys):
    dest = tmp_path / "skills"
    args = ["install", "setting-up-a-project", "setting-up-a-project", "--dest"]
    assert main([*args, str(dest)]) == 0
    assert os.listdir(dest) == ["setting-up-a-project"]
    assert capsys.readouterr().out.count("Installed") == 1


def test_unknown_skill(tmp_path, capsys):
    assert main(["install", "nope", "-d", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "scmd skills install: error: unknown skill nope" in err
    assert "migrating-from-0x, setting-up-a-project" in err
    assert os.listdir(tmp_path) == []


def test_existing_folders_need_force(tmp_path, capsys):
    (tmp_path / "setting-up-a-project").mkdir()
    (tmp_path / "setting-up-a-project" / "mine.md").write_text("kept")
    assert main(["install", "-d", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "setting-up-a-project exists" in err
    assert "Nothing copied; --force replaces these folders." in err
    assert os.listdir(tmp_path) == ["setting-up-a-project"]
    assert main(["install", "-d", str(tmp_path), "--force"]) == 0
    assert files(tmp_path / "setting-up-a-project") == files(
        PACKAGE / "setting-up-a-project"
    )


def test_force_replaces_a_file(tmp_path):
    (tmp_path / "migrating-from-0x").write_text("a file")
    assert main(["install", "migrating-from-0x", "-d", str(tmp_path), "-f"]) == 0
    assert (tmp_path / "migrating-from-0x" / "SKILL.md").is_file()


def test_force_replaces_a_link_not_its_target(tmp_path):
    target = tmp_path / "elsewhere"
    target.mkdir()
    (target / "keep.txt").write_text("kept")
    dest = tmp_path / "skills"
    dest.mkdir()
    try:
        (dest / "migrating-from-0x").symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("no symbolic links here")
    assert main(["install", "migrating-from-0x", "-d", str(dest), "-f"]) == 0
    assert (target / "keep.txt").read_text() == "kept"
    assert (dest / "migrating-from-0x" / "SKILL.md").is_file()


# --- migrating-from-0x: rewrite_pages.py --------------------------------------


def _rewrite_pages():
    path = PACKAGE / "migrating-from-0x" / "scripts" / "rewrite_pages.py"
    spec = importlib.util.spec_from_file_location("rewrite_pages", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REWRITE = _rewrite_pages()
# a 0.x project: a plain folder target/ with packages, a nested package and
# a class folder
OLD_SOURCES = [
    "target/f.m",
    "target/+pkg/g.m",
    "target/+pkg/+sub/s.m",
    "target/@Cls/Cls.m",
    "+top/t.m",
]


@pytest.fixture
def old_root(tmp_path):
    for ref in OLD_SOURCES:
        (tmp_path / ref).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / ref).write_text("function x\nend\n")
    return tmp_path


def rewritten(root, text):
    notes = []
    return REWRITE.rewrite(root, text, notes, "page.rst"), notes


@pytest.mark.parametrize(
    ("old", "new"),
    [
        # a package: its namespace, by MATLAB name
        (".. automodule:: target.+pkg", ".. mat:autonamespace:: pkg"),
        (".. mat:automodule:: target.pkg", ".. mat:autonamespace:: pkg"),
        (".. module:: target.+pkg", ".. mat:namespace:: pkg"),
        (".. automodule:: target.+pkg.+sub", ".. mat:autonamespace:: pkg.sub"),
        (".. automodule:: +top", ".. mat:autonamespace:: top"),
        ("```{automodule} target.+pkg", "```{mat:autonamespace} pkg"),
        # a plain folder, a current module and a class folder: folder forms
        (".. automodule:: target", ".. mat:autofolder:: target/"),
        (".. module:: target", ".. mat:folder:: target/"),
        (".. currentmodule:: target.+pkg", ".. mat:currentfolder:: target/+pkg/"),
        (".. automodule:: target.@Cls", ".. mat:currentfolder:: target/@Cls/"),
        (".. automodule:: .", ".. mat:currentfolder:: ."),
        # roles
        (":mat:mod:`target.+pkg`", ":mat:namespace:`pkg`"),
        (":mat:mod:`~target.+pkg.+sub`", ":mat:namespace:`~pkg.sub`"),
        ("{mat:mod}`target.+pkg`", "{mat:namespace}`pkg`"),
        (":mod:`target`", ":mat:folder:`target/`"),
    ],
)
def test_rewrite_modules(old_root, old, new):
    text, _ = rewritten(old_root, f"{old}\n")
    assert text == f"{new}\n"


def test_names_after_a_package_resolve_in_its_folder(old_root):
    text, notes = rewritten(
        old_root,
        ".. automodule:: target.+pkg\n   :members:\n\n"
        ".. autofunction:: g\n\n.. autofunction:: +sub.s\n\nSee :func:`g`.\n",
    )
    assert text == (
        ".. mat:autonamespace:: pkg\n   :members:\n\n"
        ".. autofunction:: target/+pkg/g.m\n\n"
        ".. autofunction:: target/+pkg/+sub/s.m\n\n"
        "See :func:`target/+pkg/g.m`.\n"
    )
    assert notes == []


def test_namespace_of():
    assert REWRITE.namespace_of("target/+pkg/+sub/") == "pkg.sub"
    assert REWRITE.namespace_of("+top/") == "top"
    assert REWRITE.namespace_of("target/") is None
    assert REWRITE.namespace_of("./") is None
    # a + folder in a class folder is no namespace
    assert REWRITE.namespace_of("target/@Cls/+p/") is None


def test_rewrite_keeps_inherited_members():
    """The page rewrite removes ``:special-members:`` but keeps
    ``:inherited-members:``, which works in 1.0.
    """
    notes = []
    page = (
        ".. mat:autoclass:: Cls\n   :members:\n   :special-members:\n"
        "   :inherited-members: Base\n"
    )
    out = REWRITE.rewrite(Path("."), page, notes, "page.rst")
    assert out == ".. mat:autoclass:: Cls\n   :members:\n   :inherited-members: Base\n"
    assert "page.rst:3: removed :special-members:" in notes
    assert not any("inherited" in note for note in notes)
