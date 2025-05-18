import easyams as ams

def test_get_installer_git_version():

    git_version = ams.updator.get_installer_git_version()

    assert isinstance ( git_version , str), "The function should return a string"

    assert '.' in git_version, "The version number should contain at least one dot"

def test_get_installer_local_vesrion():
    local_version = ams.updator.get_installer_local_version()
    assert isinstance ( local_version , str), "The function should return a string"
    assert '.' in local_version, "The version number should contain at least one dot"

def test_get_pipy_version():
    pypi_version = ams.updator.get_package_pypi_version()
    assert isinstance ( pypi_version , str), "The function should return a string"
    assert '.' in pypi_version, "The version number should contain at least one dot"
