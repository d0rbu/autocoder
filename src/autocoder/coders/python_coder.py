import os
import json
from warnings import warn
from typing import Any, Set, Sequence, Type, Iterable, Literal
from functools import partialmethod
from ..core.coder import Coder
from ..models.openai import OpenAIWrapper
from .openai_utils import openai_system_user_prompt, openai_tool, openai_system_prompt, openai_assistant_prompt, openai_user_prompt, openai_code_writing_tools
from ..core.tests import Tests
from ..tests.python_tests import PythonTests


class PythonOpenAICoder(Coder):
    def __init__(
        self,
        key: str,
        organization: str | None = None,
        project_home: os.PathLike = os.getcwd(),
        **default_generate_config: dict[str, Any]
    ) -> None:
        model_name = default_generate_config.get("model", "gpt-4-turbo")
        self.model = OpenAIWrapper(key, organization, model=model_name, **default_generate_config)
        self.project_home = project_home

    def refine(self, specification: Any, files: Set[os.PathLike], feedback: str) -> Set[os.PathLike]:
        model_input = [
            openai_system_prompt("You are an assistant that takes in a design specification, a codebase, and feedback from running automated tests. You must rewrite the codebase to match the specification and address feedback, if it needs to be rewritten. If you write code, ONLY write the code, no explanations or anything before or after. Previous code written will be shortened to <code>."),
        ]

        return self._write_code_loop(model_input)

    def code(self, code_design: str) -> Set[os.PathLike]:
        model_input = [
            openai_system_prompt("You are an coding assistant that takes in a design document and creates code that meets the design document. If you write code, ONLY write the code, no explanations or anything before or after. Previous code written will be shortened to <code>."),
        ]

        return self._write_code_loop(model_input, overwrite_files=False)  # Only write new code into new files, don't overwrite existing files.

    PATH_CODE_SEPARATOR = "\n\n"

    def _generate_tests(self, test_type: Literal["unit", "integration"], specification: Any, files_to_test: Set[os.PathLike], existing_test_files: Set[os.PathLike] = set()) -> Tests:
        codebase = {file: open(file, encoding="utf-8").read() for file in files_to_test}
        existing_tests = {file: open(file, encoding="utf-8").read() for file in existing_test_files}

        model_input = [
            openai_system_prompt(f"You are an assistant that takes in a design specification, a codebase, and a list of existing {test_type} tests. You must rewrite the existing {test_type} tests to match the specification, if they need to be rewritten. If you write code, ONLY write the code for the {test_type} tests, no explanations or anything before or after. Previous tests written will be shortened to <tests>."),
            openai_assistant_prompt("What is your design specification?"),
            openai_user_prompt(specification),
            openai_assistant_prompt("What is your codebase?"),
            *[
                openai_user_prompt(f"{path}{self.PATH_CODE_SEPARATOR}{code}")
                for path, code in codebase.items()
            ],
            openai_assistant_prompt(f"What are the existing {test_type} tests?"),
            *[
                openai_user_prompt(f"{path}{self.PATH_CODE_SEPARATOR}{code}")
                for path, code in existing_tests.items()
            ],
        ]

        modified_files = self._write_code_loop(model_input, code_type="tests")
        
        return PythonTests(modified_files, self.project_home)

    generate_unit_tests = partialmethod(_generate_tests, "unit")
    generate_integration_tests = partialmethod(_generate_tests, "integration")

    def _write_code_loop(self, model_input: list[str], code_type: Literal["tests", "code"] = "code", max_code_files: int = 5, overwrite_files: bool = True) -> None:
        modified_files = set()
        current_file = None
        for _ in range(max_code_files):
            response = self.model(messages=model_input, tools=openai_code_writing_tools, tool_choice="auto")
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            finished_writing_code = False
            write_code_to_file = True

            if tool_calls:
                for tool_call in tool_calls:
                    if tool_call.function.name == "select_file":
                        current_file = tool_call.function.arguments.get("file")

                        if not overwrite_files and os.path.exists(current_file):
                            parent_directory = os.path.dirname(current_file)
                            
                            model_input.append(openai_user_prompt(f"File {current_file} already exists. Please select another file to write to. Files in {parent_directory} are: {os.listdir(parent_directory)}"))
                            write_code_to_file = False
                        else:
                            model_input.append(openai_assistant_prompt(f"I will write {code_type} in {current_file}:"))
                            modified_files.add(current_file)
                    elif tool_call.function.name == "finish_writing_code":
                        finished_writing_code = True
                    else:
                        warn(f"Unknown tool call: {tool_call}")
            
            if finished_writing_code:
                break

            if not (response_message.content and write_code_to_file):
                continue

            if current_file is None:
                warn("Wanted to write code but no file selected to write code in.")
                continue
            
            with open(current_file, "w", encoding="utf-8") as f:
                f.write(response_message.content)
            
            model_input.append(openai_assistant_prompt(f"<{code_type}>"))
        
        return modified_files

    def choose_subcoder(self, task: str, allowed_subcoders: Iterable[Type[Coder]]) -> Coder:
        model_input = openai_system_user_prompt("You are an assistant that must choose a subcoder to complete the following task.", task)

        tools = [
            openai_tool(
                name="choose_subcoder",
                description="Choose a subcoder to complete the given task.",
                parameters={
                    "type": "object",
                    "properties": {
                        "subcoder": {
                            "type": "string",
                            "enum": [subcoder.__name__ for subcoder in allowed_subcoders],
                        },
                    },
                    "required": ["subcoder"],
                },
            )
        ]

        response = self.model(messages=model_input, tools=tools, tool_choice="choose_subcoder")

        subcoder_name = response.choices[0].message.tool_calls[0].function.arguments.get("subcoder")
        subcoder_class = allowed_subcoders[subcoder_name]

        return subcoder_class()
    
    @property
    def subcoders(self) -> Iterable[Type[Coder]]:
        return (PythonOpenAICoder,)

    def generate_dev_plan(self, code_design: str, max_tokens: int = 4096) -> Sequence[str]:
        model_input = openai_system_user_prompt("You are an assistant that takes in a design document and creates a list of action items necessary to complete the task.  Your requirements are:\n1. You must return a JSON list of strings. (e.g. [\"item1\", \"item2\", \"item3\"])\n2. Each item should be clear and concise.", code_design)

        response = self.model(messages=model_input, response_format={ "type": "json_object" }, max_tokens=max_tokens)
        return json.loads(response.choices[0].message.content)

    def should_generate_dev_plan(self, code_design: str) -> bool:
        model_input = openai_system_user_prompt("You are an assistant that takes in a code design and determines if it is too complex to be coded within thirty minutes and within one to three files. Call set_code_complexity once.", code_design)

        tools = [
            openai_tool(
                name="set_code_complexity",
                description="If true, the code is too complex. If false, the code simple enough.",
                parameters={
                    "type": "object",
                    "properties": {
                        "code_is_complex": {
                            "type": "bool",
                            "description": "Whether the code is too complex to be coded within thirty minutes in 1-3 files.",
                        },
                    },
                    "required": ["code_is_complex"],
                },
            )
        ]

        response = self.model(messages=model_input, tools=tools, tool_choice="set_code_complexity")
        return response.choices[0].message.tool_calls[0].function.arguments.get("code_is_complex")
    
    def design_solution(self, specification: Any) -> str:
        model_input = openai_system_user_prompt("You are an assistant that helps me generate design documents. Your requirements are: \n1. Design a system that meets the following specification.\n2. You must use Python.\n3. You must specify all frameworks used. (e.g. This will be built in Django and will utilize OpenCV)\n4. Make sure to be extremely detailed", specification)
        response = self.model(messages=model_input)
        return response.choices[0].message.content