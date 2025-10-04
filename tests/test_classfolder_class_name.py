from sphinxcontrib.matlab.mat_types import classfolder_class_name


def test_classfolders():
    name = classfolder_class_name("target.@ClassFolder")
    assert name == "target.@ClassFolder"

    name = classfolder_class_name("target.@ClassFolder.Func")
    assert name == "target.@ClassFolder.Func"

    name = classfolder_class_name("target.@ClassFolder.ClassFolder")
    assert name == "target.ClassFolder"

    name = classfolder_class_name("target.+pkg.@ClassFolder.ClassFolder")
    assert name == "target.+pkg.ClassFolder"

    name = classfolder_class_name("@ClassFolder")
    assert name == "@ClassFolder"

    name = classfolder_class_name("@ClassFolder.Func")
    assert name == "@ClassFolder.Func"

    name = classfolder_class_name("@ClassFolder.ClassFolder")
    assert name == "ClassFolder"
