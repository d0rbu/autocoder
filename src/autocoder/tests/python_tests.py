import subprocess
from typing import Sequence, Tuple, Any, Set
from io import StringIO
from pathlib import Path
import sys
import os
import pytest
from ..core.tests import Tests


class PythonTests(Tests):
    """
    Representation of Python tests. Uses pytest to run tests.
    """

    def __init__(self, test_files: Set[os.PathLike], python_executable: os.PathLike = Path('python'), project_home: os.PathLike | None = None) -> None:
        super().__init__(project_home)
        self.main_test_files = test_files
        self.other_tests = set()
        self.python_executable = python_executable

    def combine(self, tests: Tests) -> Tests:
        if isinstance(tests, PythonTests):
            self.main_test_files |= tests.main_test_files
            return self

        self.other_tests.add(tests)
        return self

    def test_files(self) -> Sequence[os.PathLike]:
        return [*self.test_files, *[other_test.test_files() for other_test in self.other_tests]]

    TEST_RESULT_SEPARATOR = '\n\n'

    def run(self) -> Tuple[bool, Any]:
        test_output = subprocess.run([self.python_executable, '-m', 'pytest', *self.main_test_files], capture_output=True, check=False)

        other_test_results = [other_test.run() for other_test in self.other_tests]

        main_test_successful = test_output.returncode == 0
        other_tests_successful = all([result[0] for result in other_test_results])

        other_test_results = [result[1] for result in other_test_results]
        joined_test_results = self.TEST_RESULT_SEPARATOR.join([test_output.stdout.decode("utf-8"), *other_test_results])

        return (main_test_successful and other_tests_successful), joined_test_results
