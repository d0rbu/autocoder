import pytest
from autocoder.coders.python_coder import PythonOpenAICoder


def test_create_coder_happypath():
    expected_top_p = 0.7
    expected_project_home = "test_project_home"

    test_coder = PythonOpenAICoder(
        key="test_key",
        organization="test_organization",
        project_home=expected_project_home,
        top_p=expected_top_p
    )

    assert test_coder.model is not None
    assert test_coder.model.default_generate_config.get("top_p") == expected_top_p
    assert test_coder.project_home == expected_project_home

@pytest.mark.dependency(depends=["test_create_coder_happypath"])
@pytest.fixture
def test_coder():
    return PythonOpenAICoder(
        key="test_key",
        organization="test_organization",
        project_home="test_project_home",
    )
