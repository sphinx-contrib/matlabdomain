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
    assert name == "ClassFolder"

    name = shortest_name("target.@ClassFolder.Func")
    assert name == "ClassFolder.Func"
