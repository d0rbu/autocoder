import os
import json
from pathlib import Path
from warnings import warn
from typing import Any, Set, Sequence, Type, Iterable, Literal, Mapping
from abc import ABC
from .coder import Coder
from .prompt_utils import system_user_prompt, tool, assistant_prompt, user_prompt, code_writing_tools, use_openai_tool
from .utils import DEFAULT_PERMISSIONS, parse_chat
from ..models.openai import OpenAIWrapper


class OpenAICoder(Coder, ABC):
    def __init__(
        self,
        key: str,
        organization: str | None = None,
        project_home: os.PathLike = os.getcwd(),
        rate_limit_rpm: int = 500,
        **default_generate_config: dict[str, Any],
    ) -> None:
        default_config = self.default_config.copy()
        default_config.update(default_generate_config)

        self.model = OpenAIWrapper(key, organization, rate_limit_rpm, **default_config)
        self.project_home = project_home

    @property
    def default_config(self) -> dict[str, Any]:
        """
        Get the default configuration parameters for code generation.

        Returns:
            dict[str, Any]: The default configuration.
        """
        return {}

    def _write_code_loop(self, model_input: list[str], code_type: Literal["tests", "code"] = "code", max_responses: int = 5, overwrite_files: bool = True) -> None:
        modified_files = set()
        created_files = set()
        for _ in range(max_responses):
            response = self.model(model_input=model_input, tools=code_writing_tools, tool_choice="auto")
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            finished_writing_code = False

            if tool_calls:
                for tool_call in tool_calls:
                    if tool_call.function.name == "finish":
                        finished_writing_code = True
                    else:
                        warn(f"Unknown tool call: {tool_call}")
            
            if finished_writing_code:
                break

            codeblocks = parse_chat(response_message.content)

            for path, code in codeblocks:
                current_file = os.path.join(self.project_home, path)
                if not os.path.exists(current_file):
                    created_files.add(current_file)
                    modified_files.add(current_file)
                    Path(current_file).touch()
                    os.chmod(current_file, DEFAULT_PERMISSIONS)

                if not overwrite_files and current_file not in created_files:  # Don't overwrite existing files, but you can write to files that you created
                    parent_directory = os.path.dirname(current_file)

                    model_input.append(user_prompt(f"File {current_file} already exists. Please select another file to write to. Files in {parent_directory} are: {os.listdir(parent_directory)}"))
                else:
                    with open(current_file, "w", encoding="utf-8") as f:
                        f.write(code)

                    model_input.append(assistant_prompt(f"{path}\n<{code_type}>"))
                    modified_files.add(current_file)
        
        return modified_files

    _refine = _write_code_loop
    
    def _code(self, model_input: Sequence[Mapping[str, str]]) -> Set[os.PathLike]:
        return self._write_code_loop(model_input, overwrite_files=False)

    def _generate_tests(self, model_input: Sequence[Mapping[str, str]]) -> Set[os.PathLike]:
        return self._write_code_loop(model_input, code_type="tests")

    _generate_unit_tests = _generate_tests
    _generate_integration_tests = _generate_tests

    def _choose_subcoder(self, task: str, allowed_subcoders: Iterable[Type[Coder]]) -> Coder:
        model_input = system_user_prompt("You are an assistant that must choose a subcoder to complete the following task.", task)

        tools = [
            tool(
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

        response = self.model(model_input=model_input, tools=tools, tool_choice=use_openai_tool("choose_subcoder"))

        subcoder_name = response.choices[0].message.tool_calls[0].function.arguments.get("subcoder")
        subcoder_class = allowed_subcoders[subcoder_name]

        return subcoder_class()

    def generate_dev_plan(self, code_design: str, max_tokens: int = 4096) -> Sequence[str]:
        model_input = system_user_prompt("You are an assistant that takes in a code design and creates a list of action items necessary to complete the task.  Your requirements are:\n1. You must return a JSON list of strings. (e.g. [\"item1\", \"item2\", \"item3\"])\n2. Each item should be clear and concise.", code_design)

        response = self.model(model_input=model_input, response_format={ "type": "json_object" }, max_tokens=max_tokens)
        return json.loads(response.choices[0].message.content)

    def should_generate_dev_plan(self, code_design: str) -> bool:
        model_input = system_user_prompt("You are an assistant that takes in a code design and determines if it is too complex to be coded within thirty minutes and within one to three files. Call set_code_complexity once.", code_design)

        tools = [
            tool(
                name="set_code_complexity",
                description="If true, the code is too complex. If false, the code is simple enough.",
                parameters={
                    "type": "object",
                    "properties": {
                        "code_is_complex": {
                            "type": "boolean",
                            "description": "Whether the code is too complex to be coded within thirty minutes in 1-3 files.",
                        },
                    },
                    "required": ["code_is_complex"],
                },
            )
        ]

        response = self.model(model_input=model_input, tools=tools, tool_choice=use_openai_tool("set_code_complexity"))
        return response.choices[0].message.tool_calls[0].function.arguments.get("code_is_complex")
