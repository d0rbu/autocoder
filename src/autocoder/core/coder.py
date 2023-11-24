from abc import ABC, abstractmethod
import os
from typing import Sequence, Type, Self, Tuple, Set, Any
from .tests import Tests


class Coder(ABC):
    """
    Base class for all coders.

    The coder is responsible for generating the code that fit the given specification.
    It designs the code structure and logic and decides if it can do it all in one shot or not.
    If not, it will break the task into smaller tasks and delegate them to other coders.
    Then, after coding, whether it be in one shot or in multiple shots, it will use a feeedback
    loop to improve the code until it fits the specification and passes all tests.
    """

    DEFAULT_TESTS_DIR = "tests"

    def build(
        self,
        specification: Any,
        scaffolded: bool = False,
        project_home: os.PathLike | None = None,
    ) -> Tuple[Set[os.PathLike], Tests]:
        """
        Build the code.

        Args:
            specification (str): The specification of the code to build.

        Returns:
            Tuple[Sequence[os.PathLike], Tests]: The paths to the files generated/modified by the coder and the tests.
        """
        touched_project_files = set()
        touched_test_files = set()
        project_home = project_home or os.getcwd()

        code_design = self.design_solution(specification)

        if not scaffolded:
            touched_project_files.update(self.scaffold(code_design))

        # Generate first version of the code
        unit_tests = None
        if self.should_generate_dev_plan(code_design):
            dev_plan = self.generate_dev_plan(code_design)

            for dev_step in dev_plan:
                subcoder = self.choose_subcoder(dev_step, self.allowed_subcoders)

                subcoder_touched_files, subcoder_tests = subcoder.build(specification=dev_step, scaffolded=True, project_home=project_home)
                touched_project_files.update(subcoder_touched_files)

                if unit_tests is None:
                    unit_tests = subcoder_tests
                else:
                    unit_tests += subcoder_tests
        else:  # Base case
            touched_project_files.update(self.code(code_design))

        generate_integration_tests = unit_tests is not None  # If there are unit tests, then we need to generate integration tests. Otherwise, we don't.

        # Generate first version of the tests
        # Purposely exclude existing unit tests if there are any, since we want to specifically generate integration tests.
        generated_tests = self.generate_tests(specification, touched_project_files, integration=generate_integration_tests)
        generated_tests += unit_tests

        touched_test_files.update(generated_tests.test_files())

        # After finished generating first iteration, enter refinement loop.
        passes_tests, test_results = generated_tests.run()
        while not passes_tests:
            feedback = self.feedback_hook(test_results)
            touched_project_files.update(self.refine(specification, touched_project_files, feedback))

            new_tests = self.generate_tests(specification, touched_project_files, integration=generate_integration_tests, existing_test_files=touched_test_files)
            generated_tests += new_tests

            if new_tests is not None:
                touched_test_files.update(new_tests.test_files())

            passes_tests, test_results = generated_tests.run()

        return touched_project_files | touched_test_files

    def feedback_hook(self, test_results: Any) -> str:
        """
        Hook to modify the feedback before refining the code.

        Args:
            test_results (str): The results of the tests.

        Returns:
            str: The feedback on the code.
        """
        if isinstance(test_results, str):
            return test_results

        return ""

    @abstractmethod
    def refine(self, specification: Any, files: Set[os.PathLike], feedback: str) -> Set[os.PathLike]:
        """
        Refine the code.

        Args:
            specification (str): The specification of the code to build.
            files (Set[os.PathLike]): The files to refine.
            feedback (str): The feedback to use to refine the code.

        Returns:
            Set[os.PathLike]: Paths to the files generated/modified by the coder.
        """

    def generate_tests(self, specification: Any, files_to_test: Set[os.PathLike], existing_test_files: Set[os.PathLike] | None = None, integration: bool = False) -> Tests | None:
        """
        Generate the tests. If there are existing tests that already adequately test the code, then this method may return None.

        Args:
            specification (str): The specification of the code to build.
            files_to_test (Set[os.PathLike]): The files to test.
            existing_test_files (Set[os.PathLike], optional): The files that already contain tests. Defaults to None.
            integration (bool, optional): Whether to generate integration tests or unit tests. Defaults to False.

        Returns:
            Tests | None: The tests for the code, if any.
        """
        if integration:
            return self.generate_integration_tests(specification, files_to_test, existing_test_files)

        return self.generate_unit_tests(specification, files_to_test, existing_test_files)

    @abstractmethod
    def generate_integration_tests(self, specification: Any, files_to_test: Set[os.PathLike], existing_test_files: Set[os.PathLike] | None = None) -> Tests:
        """
        Generate the integration tests.

        Args:
            specification (str): The specification of the code to build.
            files_to_test (Set[os.PathLike]): The files to test.
            existing_test_files (Set[os.PathLike], optional): The files that already contain tests. Defaults to None.

        Returns:
            Tests: The integration tests for the code.
        """

    @abstractmethod
    def generate_unit_tests(self, specification: Any, files_to_test: Set[os.PathLike], existing_test_files: Set[os.PathLike] | None = None) -> Tests:
        """
        Generate the unit tests.

        Args:
            specification (str): The specification of the code to build.
            files_to_test (Set[os.PathLike]): The files to test.
            existing_test_files (Set[os.PathLike], optional): The files that already contain tests. Defaults to None.

        Returns:
            Tests: The unit tests for the code.
        """

    def tests_directory(self, project_home: os.PathLike) -> os.PathLike:
        """
        Get the directory where the tests are stored.

        Args:
            project_home (os.PathLike): The path to the project home.

        Returns:
            os.PathLike: The path to the tests directory.
        """
        return os.path.join(project_home, self.DEFAULT_TESTS_DIR)

    @abstractmethod
    def code(self, code_design: str) -> Set[os.PathLike]:
        """
        Generate the code.

        Args:
            code_design (str): The explanation of how the code should be structured and how it should work.

        Returns:
            Set[os.PathLike]: Paths to the files generated/modified by the coder.
        """

    @property
    @abstractmethod
    def allowed_subcoders(self) -> Sequence[Type[Self]]:
        """
        The set of coders that can be used to delegate tasks to.
        """

    @abstractmethod
    def choose_subcoder(self, task: str, allowed_subcoders: Sequence[Type[Self]]) -> Self:
        """
        Choose and return subcoder to delegate a task to.

        Args:
            task (str): The task to delegate.
            allowed_subcoders (Sequence[Type[Coder]]): The set of coders to choose from.

        Returns:
            Coder: The chosen coder.
        """

    @abstractmethod
    def generate_dev_plan(self, code_design: str) -> Sequence[str]:
        """
        Generate a development plan.

        Args:
            code_design (str): The explanation of how the code should be structured and how it should work.

        Returns:
            Sequence[str]: The steps to follow to implement the design.
        """

    @abstractmethod
    def should_generate_dev_plan(self, code_design: str) -> bool:
        """
        Decide whether to generate a development plan or not.

        Args:
            code_design (str): The explanation of how the code should be structured and how it should work.

        Returns:
            bool: Whether to generate a development plan or not.
        """

    @abstractmethod
    def scaffold(self, code_design: str) -> Set[os.PathLike]:
        """
        Generate the project structure and perform setup tasks.

        Args:
            code_design (str): The explanation of how the code should be structured and how it should work.

        Returns:
            Set[os.PathLike]: Paths to the files generated/modified by the setup process.
        """

    @abstractmethod
    def design_solution(self, specification: Any) -> str:
        """
        Design the architecture and logic of the code.

        Args:
            specification (str): The specification of the code to build.

        Returns:
            str: The explanation of how the code should be structured and how it should work.
        """
