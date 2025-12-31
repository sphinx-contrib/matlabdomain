from sphinxcontrib.mat_types import shortest_name


def test_no_alternative():
    name = shortest_name("Class")
    assert name == "Class"

    name = shortest_name("")
    assert name == ""


def test_packages():
    name = shortest_name("+package.Function")
    assert name == "package.Function"

    name = shortest_name("sub.+package.Function")
    assert name == "package.Function"

    name = shortest_name("sub.+package.Function")
    assert name == "package.Function"

    name = shortest_name("sub.+package.+level.Function")
    assert name == "package.level.Function"


def test_folders():
    name = shortest_name("sub1.sub2.sub3.Function")
    assert name == "Function"

    name = shortest_name("sub1.Function")
    assert name == "Function"


def test_weird():
    name = shortest_name("sub1.+sub2.sub3.Function")
    assert name == "Function"


def test_classfolders():
    name = shortest_name("target.@ClassFolder")
    assert name == "target.@ClassFolder"

    name = shortest_name("target.@ClassFolder.Func")
    assert name == "target.@ClassFolder.Func"

    name = shortest_name("target.@ClassFolder.ClassFolder")
    assert name == "target.@ClassFolder.ClassFolder"

    name = shortest_name("target.+pkg.@ClassFolder.ClassFolder")
    assert name == "target.+pkg.@ClassFolder.ClassFolder"

    name = shortest_name("@ClassFolder")
    assert name == "@ClassFolder"

    name = shortest_name("@ClassFolder.Func")
    assert name == "@ClassFolder.Func"

    name = shortest_name("@ClassFolder.ClassFolder")
    assert name == "@ClassFolder.ClassFolder"
