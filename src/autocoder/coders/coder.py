import os
from abc import ABC, abstractmethod
from typing import Sequence, Type, Self, Tuple, Set, Any, Iterable, Literal
from functools import partialmethod
from .prompt_utils import system_prompt, assistant_prompt, user_prompt
from ..tests.tests import Tests, NoTests


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
    PATH_CODE_SEPARATOR = "\n\n"

    def build(
        self,
        specification: Any,
        project_home: os.PathLike | None = None,
    ) -> Tuple[Set[os.PathLike], Tests]:
        """
        Build the code.

        Args:
            specification (str): The specification of the code to build.

        Returns:
            Tuple[Set[os.PathLike], Tests]: The paths to the files generated/modified by the coder and the tests.
        """
        touched_project_files = set()
        touched_test_files = set()
        project_home: os.PathLike = project_home or os.getcwd()

        code_design = self.design_solution(specification)

        touched_project_files.update(self.scaffold(code_design, project_home))

        # Generate first version of the code
        unit_tests = NoTests()
        if self.should_generate_dev_plan(code_design):
            dev_plan = self.generate_dev_plan(code_design)

            for dev_step in dev_plan:
                subcoder = self.choose_subcoder(dev_step, self.allowed_subcoders)

                subcoder_touched_files, subcoder_tests = subcoder.build(specification=dev_step, project_home=project_home)
                touched_project_files.update(subcoder_touched_files)

                unit_tests += subcoder_tests
        else:  # Base case
            touched_project_files.update(self.code(code_design))

        should_generate_integration_tests = isinstance(unit_tests, NoTests)  # If there are unit tests, then we need to generate integration tests. Otherwise, we don't.

        # Generate first version of the tests
        # Purposely exclude existing unit tests if there are any, since we want to specifically generate integration tests.
        generated_tests = self.generate_tests(specification, touched_project_files, integration=should_generate_integration_tests)
        generated_tests += unit_tests

        touched_test_files.update(generated_tests.test_files())

        # After finished generating first iteration, enter refinement loop.
        passes_tests, test_results = generated_tests.run()
        while not passes_tests:
            feedback = self.feedback_hook(test_results)
            touched_project_files.update(self.refine(specification, touched_project_files, feedback))

            new_tests = self.generate_tests(specification, touched_project_files, integration=should_generate_integration_tests, existing_test_files=touched_test_files, test_results=test_results)
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

    def tests_directory(self, project_home: os.PathLike) -> os.PathLike:
        """
        Get the directory where the tests are stored.

        Args:
            project_home (os.PathLike): The path to the project home.

        Returns:
            os.PathLike: The path to the tests directory.
        """
        return os.path.join(project_home, self.DEFAULT_TESTS_DIR)

    def choose_subcoder(self, task: str, allowed_subcoders: Set[Type[Self]]) -> Self:
        """
        Choose and return subcoder to delegate a task to.

        Args:
            task (str): The task to delegate.
            allowed_subcoders (Set[Type[Coder]]): The set of coders to choose from.

        Returns:
            Coder: The chosen coder.
        """
        if len(allowed_subcoders) == 0:
            raise ValueError("No coders to choose from.")

        return self._choose_subcoder(task, allowed_subcoders)
    
    def _read_files(self, files: Set[os.PathLike]) -> str:
        file_contents = {}
        for file in files:
            if not os.path.isfile(file):
                continue

            with open(file, encoding="utf-8") as f:
                file_contents[file] = f.read()
        
        return file_contents

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
        model_input = self._generate_refine_prompt(specification, files, feedback)

        return self._refine(self._prepare_model_input(model_input))

    def code(self, code_design: str) -> Set[os.PathLike]:
        """
        Generate the code.

        Args:
            code_design (str): The explanation of how the code should be structured and how it should work.

        Returns:
            Set[os.PathLike]: Paths to the files generated/modified by the coder.
        """
        model_input = self._generate_code_prompt(code_design)

        return self._code(self._prepare_model_input(model_input))

    def generate_tests(self, specification: Any, files_to_test: Set[os.PathLike], existing_test_files: Set[os.PathLike] | None = None, project_home: os.PathLike | None = None, integration: bool = False, test_results: Any = None) -> Tests:
        """
        Generate the tests. If there are existing tests that already adequately test the code, then this method may return None.

        Args:
            specification (str): The specification of the code to build.
            files_to_test (Set[os.PathLike]): The files to test.
            existing_test_files (Set[os.PathLike], optional): The files that already contain tests. Defaults to None.
            integration (bool, optional): Whether to generate integration tests or unit tests. Defaults to False.
            test_results (Any, optional): The results of the tests. Defaults to None.

        Returns:
            Tests: The tests for the code.
        """
        existing_test_files = existing_test_files or set()

        if integration:
            return self.generate_integration_tests(specification, files_to_test, existing_test_files, project_home, test_results)

        return self.generate_unit_tests(specification, files_to_test, existing_test_files, project_home, test_results)
    
    def generate_integration_tests(self, specification: Any, files_to_test: Set[os.PathLike], existing_test_files: Set[os.PathLike] | None = None, project_home: os.PathLike | None = None, test_results: Any = None) -> Tests:
        """
        Generate the integration tests. If there are existing tests that already adequately test the code, then this method may return None.

        Args:
            specification (str): The specification of the code to build.
            files_to_test (Set[os.PathLike]): The files to test.
            existing_test_files (Set[os.PathLike], optional): The files that already contain tests. Defaults to None.
            test_results (Any, optional): The results of the tests. Defaults to None.

        Returns:
            Tests: The tests for the code.
        """
        existing_test_files = existing_test_files or set()

        model_input = self._generate_integration_tests_prompt(specification, files_to_test, existing_test_files, test_results)

        test_files = self._generate_integration_tests(self._prepare_model_input(model_input))
    
        return self._files_to_tests(test_files, project_home)
    
    def generate_unit_tests(self, specification: Any, files_to_test: Set[os.PathLike], existing_test_files: Set[os.PathLike] | None = None, project_home: os.PathLike | None = None, test_results: Any = None) -> Tests:
        """
        Generate the unit tests. If there are existing tests that already adequately test the code, then this method may return None.

        Args:
            specification (str): The specification of the code to build.
            files_to_test (Set[os.PathLike]): The files to test.
            existing_test_files (Set[os.PathLike], optional): The files that already contain tests. Defaults to None.
            test_results (Any, optional): The results of the tests. Defaults to None.

        Returns:
            Tests: The tests for the code.
        """
        existing_test_files = existing_test_files or set()

        model_input = self._generate_unit_tests_prompt(specification, files_to_test, existing_test_files, test_results)

        test_files = self._generate_unit_tests(self._prepare_model_input(model_input))
    
        return self._files_to_tests(test_files, project_home)
    
    def _generate_refine_prompt(self, specification: Any, files: Set[os.PathLike], feedback: str) -> Any:

        codebase = self._read_files(files)
        
        model_input = [
            system_prompt("You are an assistant that takes in a design specification, a codebase, and feedback from running automated tests. You must rewrite the codebase to match the specification and address feedback, if it needs to be rewritten. If you write code, write it in the format of <path>\n<codeblock>, where <codeblock> is the code surrounded by ```. Previous code written will be shortened to <code>."),
            assistant_prompt("What is your specification?"),
            user_prompt(specification),
            assistant_prompt("What is your codebase?"),
            *[
                user_prompt(f"{path}{self.PATH_CODE_SEPARATOR}{code}")
                for path, code in codebase.items()
            ],
            assistant_prompt("What is the feedback from testing?"),
            user_prompt(feedback),
            assistant_prompt("Entering code writing mode..."),
        ]

        return model_input
    
    def _generate_code_prompt(self, code_design: str) -> Any:
        model_input = [
            system_prompt("You are an coding assistant that takes in a design document and creates code that meets the design document. If you write code, write it in the format of <path>\n<codeblock>, where <codeblock> is the code surrounded by ```. Previous code written will be shortened to <code>."),
            assistant_prompt("What is your code design?"),
            user_prompt(code_design),
            assistant_prompt("Entering code writing mode. I will only make function calls if I absolutely have to, otherwise I will just be writing code..."),
        ]

        return model_input

    def _generate_tests_prompt(self, test_type: Literal["integration", "unit"], specification: Any, files_to_test: Set[os.PathLike], existing_test_files: Set[os.PathLike] | None = None, test_results: Any = None) -> Any:
        existing_test_files = existing_test_files or set()

        codebase = self._read_files(files_to_test)
        existing_tests = self._read_files(existing_test_files)

        model_input = [
            system_prompt(f"You are an assistant that takes in a design specification, a codebase, and a list of existing {test_type} tests. You must rewrite the existing {test_type} tests to match the specification, if they need to be rewritten. If you write code, write it in the format of <path>\n<codeblock>, where <codeblock> is the code surrounded by ```. Previous tests written will be shortened to <tests>."),
            assistant_prompt("What is your design specification?"),
            user_prompt(specification),
            assistant_prompt("What is your codebase?"),
            *[
                user_prompt(f"{path}{self.PATH_CODE_SEPARATOR}{code}")
                for path, code in codebase.items()
            ],
            assistant_prompt(f"What are the existing {test_type} tests?"),
            *[
                user_prompt(f"{path}{self.PATH_CODE_SEPARATOR}{code}")
                for path, code in existing_tests.items()
            ],
        ]

        if test_results is not None:
            model_input.extend([
                assistant_prompt("What are previous test results?"),
                user_prompt(test_results),
            ])
        
        model_input.append(assistant_prompt("Entering test writing mode. I will only make function calls if I absolutely have to, otherwise I will just be writing code..."))
        
        return model_input

    _generate_integration_tests_prompt = partialmethod(_generate_tests_prompt, "integration")
    _generate_unit_tests_prompt = partialmethod(_generate_tests_prompt, "unit")

    def _prepare_model_input(self, model_input: Any) -> Any:
        return model_input


    @abstractmethod
    def _refine(self, model_input: Any) -> Set[os.PathLike]:
        """
        Refine the code.

        Args:
            model_input (Any): The input to the model from _generate_refine_prompt.

        Returns:
            Set[os.PathLike]: Paths to the files generated/modified by the coder.
        """
    
    @abstractmethod
    def _code(self, model_input: Any) -> Set[os.PathLike]:
        """
        Generate the code.

        Args:
            model_input (Any): The input to the model from _generate_code_prompt.

        Returns:
            Set[os.PathLike]: Paths to the files generated/modified by the coder.
        """

    @abstractmethod
    def _generate_integration_tests(self, model_input: Any) -> Set[os.PathLike]:
        """
        Generate the integration tests.

        Args:
            model_input (Any): The input to the model from _generate_integration_tests_prompt.

        Returns:
            Set[os.PathLike]: Paths to the files generated/modified by the coder.
        """
    
    @abstractmethod
    def _generate_unit_tests(self, model_input: Any) -> Set[os.PathLike]:
        """
        Generate the unit tests.

        Args:
            model_input (Any): The input to the model from _generate_unit_tests_prompt.

        Returns:
            Set[os.PathLike]: Paths to the files generated/modified by the coder.
        """


    @property
    @abstractmethod
    def allowed_subcoders(self) -> Iterable[Type[Self]]:
        """
        The set of coders that can be used to delegate tasks to.
        """

    @abstractmethod
    def _choose_subcoder(self, task: str, allowed_subcoders: Iterable[Type[Self]]) -> Self:
        """
        Choose and return subcoder to delegate a task to.

        Args:
            task (str): The task to delegate.
            allowed_subcoders (Iterable[Type[Coder]]): The set of coders to choose from, there's always at least one.

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
    def scaffold(self, code_design: str, project_home: os.PathLike) -> Set[os.PathLike]:
        """
        Generate the project structure and perform setup tasks.

        Args:
            code_design (str): The explanation of how the code should be structured and how it should work.
            project_home (os.PathLike): The path to the project home.

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

    @abstractmethod
    def _files_to_tests(self, files: Set[os.PathLike], project_home: os.PathLike | None = None) -> Tests:
        """
        Convert a set of files to a Tests object.

        Args:
            files (Set[os.PathLike]): The files containing the test code.
            project_home (os.PathLike | None, optional): The path to the project home. Defaults to None.

        Returns:
            Tests: The tests.
        """
