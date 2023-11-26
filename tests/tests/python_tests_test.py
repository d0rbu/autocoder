import pytest
import os
from autocoder.tests.python_tests import PythonTests


@pytest.fixture()
def empty_pythontests():
    return PythonTests(set())

def test_empty_pythontests_files(empty_pythontests):
    expected_num_files = 0

    num_files = len(empty_pythontests.test_files())

    assert num_files == expected_num_files

def test_empty_pythontests_run(empty_pythontests):
    expected_result = (False, "")

    result = empty_pythontests.run()

    assert result == expected_result


@pytest.fixture()
def invalid_pythontests():
    return PythonTests({os.path.join("tests", "tests", "sample_tests", "invalid_test_0.py"), os.path.join("tests", "tests", "sample_tests", "invalid_test_1.py"),})

def test_invalid_pythontests_files(invalid_pythontests):
    expected_num_files = 0

    num_files = len(invalid_pythontests.test_files())

    assert num_files == expected_num_files

def test_invalid_pythontests_run(invalid_pythontests):
    expected_result = (False, "")

    result = invalid_pythontests.run()

    assert result == expected_result


@pytest.fixture()
def passing_pythontests():
    return PythonTests({os.path.join("tests", "tests", "sample_tests", "passing_tests.py"),})

def test_passing_pythontests_files(passing_pythontests):
    expected_num_files = 1

    num_files = len(passing_pythontests.test_files())

    assert num_files == expected_num_files

def test_passing_pythontests_run(passing_pythontests):
    expected_success = True

    success, _ = passing_pythontests.run()

    assert success == expected_success

@pytest.fixture()
def failing_pythontests():
    return PythonTests({os.path.join("tests", "tests", "sample_tests", "failing_tests.py"),})

def test_failing_pythontests_files(failing_pythontests):
    expected_num_files = 1

    num_files = len(failing_pythontests.test_files())

    assert num_files == expected_num_files

def test_failing_pythontests_run(failing_pythontests):
    expected_success = False

    success, _ = failing_pythontests.run()

    assert success == expected_success
