from core.tests import Tests
from typing import Sequence, Tuple, Any
from io import StringIO
import sys
import os
import pytest


class PythonTests(Tests):
    """
    Representation of Python tests. Uses pytest to run tests.
    """

    def __init__(self, test_files: Sequence[os.PathLike], project_home: os.PathLike | None = None) -> None:
        super().__init__(project_home)
        self.main_test_files = set(test_files)
        self.other_tests = []

    def combine(self, tests: Tests) -> Tests:
        if isinstance(tests, PythonTests):
            self.main_test_files |= tests.main_test_files
            return self
        
        self.other_tests.append(tests)
        return self

    def test_files(self) -> Sequence[os.PathLike]:
        return [*self.test_files, *[other_test.test_files() for other_test in self.other_tests]]
    
    TEST_RESULT_SEPARATOR = '\n\n'
    
    def run(self) -> Tuple[bool, Any]:
        original_stdout = sys.stdout

        captured_stdout = StringIO()
        sys.stdout = captured_stdout

        return_code = pytest.main(self.main_test_files)

        sys.stdout = original_stdout
        captured_output = captured_stdout.getvalue()

        other_test_results = [other_test.run() for other_test in self.other_tests]

        main_test_successful = return_code == 0
        other_tests_successful = all([result[0] for result in other_test_results])

        other_test_results = [result[1] for result in other_test_results]
        joined_test_results = self.TEST_RESULT_SEPARATOR.join([captured_output, *other_test_results])

        return (main_test_successful and other_tests_successful), joined_test_results
