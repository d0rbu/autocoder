from coders import Coder
from typing import Any, Set, Sequence, Type, Self
from models.wrapper import ModelWrapper
from models.openai import OpenAIWrapper
from utils import openai_system_user_prompt, openai_single_function
from core.tests import Tests, NoTests
import os
import json

class PythonOpenAICoder(Coder):
    def __init__(
        self,
        key: str,
        organization: str | None = None,
        **default_generate_config: dict[str, Any]
    ) -> None:
        model_name = default_generate_config.get("model", "gpt-4-turbo")
        self.model = OpenAIWrapper(key, organization, model=model_name, **default_generate_config)

    def refine(self, specification: Any, files: Set[os.PathLike], feedback: str) -> Set[os.PathLike]:

    def code(self, code_design: str) -> Set[os.PathLike]:

    def generate_integration_tests(self, specification: Any, files_to_test: Set[os.PathLike], existing_test_files: Set[os.PathLike] = set()) -> Tests:
        
    def generate_unit_tests(self, specification: Any, files_to_test: Set[os.PathLike], existing_test_files: Set[os.PathLike] = set()) -> Tests:
        codebase = {file: open(file).read() for file in files_to_test}
        existing_tests = {file: open(file).read() for file in existing_test_files}

        model_input = [
            {
                "role": "system",
                "message": "You are an assistant that takes in a design specification, a codebase, and a list of existing unit tests. You must rewrite the existing unit tests to match the specification, if they need to be rewritten. Do not write anything else, only the code for the tests.",
            },
            {
                "role": "assistant",
                "message": "What is your design specification?",
            },
            {
                "role": "user",
                "message": specification,
            },
            {
                "role": "assistant",
                "message": "What is your codebase?",
            },
            *[
                {
                    "role": "user",
                    "message": f"{path}\n\n{code}"
                }
                for path, code in codebase.items()
            ],
            {
                "role": "assistant",
                "message": "What are the existing tests?",
            },
            *[
                {
                    "role": "user",
                    "message": f"{path}\n\n{code}"
                }
                for path, code in existing_tests.items()
            ]
        ]

        response = self.model(messages=model_input)
        rewritten_tests = response.choices[0].message.content  # TODO: let model choose where to write tests, write them into there, and create PythonTests based on it

    def choose_subcoder(self, task: str, allowed_subcoders: Sequence[Type[Self]]) -> Self:
        model_input = openai_system_user_prompt("You are an assistant that must choose a subcoder to complete the following task.", task)

        tools = [
            openai_single_function(
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
    def subcoders(self) -> Sequence[Type[Self]]:
        return (PythonOpenAICoder,)

    def generate_dev_plan(self, code_design: str, max_tokens: int = 4096) -> Sequence[str]:
        model_input = openai_system_user_prompt("You are an assistant that takes in a design document and creates a list of action items necessary to complete the task.  Your requirements are:\n1. You must return a JSON list of strings. (e.g. [\"item1\", \"item2\", \"item3\"])\n2. Each item should be clear and concise.", code_design)

        response = self.model(messages=model_input, response_format={ "type": "json_object" }, max_tokens=max_tokens)
        return json.loads(response.choices[0].message.content)

    def should_generate_dev_plan(self, code_design: str) -> bool:
        model_input = openai_system_user_prompt("Only call code_multiple_pages once.", code_design)

        tools = [
            openai_single_function(
                name="code_multiple_pages",
                description="If true, the function will create multiple documents for each part of the code. If false, the function will create one document with all the code.",
                parameters={
                    "type": "object",
                    "properties": {
                        "break_pages": {
                            "type": "bool",
                            "description": "The code requires more than one page",
                        },
                    },
                    "required": ["break_pages"],
                },
            )
        ]

        response = self.model(messages=model_input, tools=tools, tool_choice="code_multiple_pages")
        return response.choices[0].message.tool_calls[0].function.arguments.get("break_pages")
        
    DEFAULT_DESIGN_SYSTEM_MESSAGE = "You are an assistant that helps me generate design documents. Your requirements are: \n1. Design a system that meets the following specification.\n2. You must use Python.\n3. You must specify all frameworks used. (e.g. Build a Django app with MySQL backend)\n4. Make sure to be extremely detailed"
    
    def design_solution(self, specification: Any, system_message: str = DEFAULT_DESIGN_SYSTEM_MESSAGE) -> str:
        model_input = openai_system_user_prompt(system_message, specification)
        response = self.model(messages=model_input)
        return response.choices[0].message.content