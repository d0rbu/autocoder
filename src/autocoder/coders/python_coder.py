from typing import Any, Type, Iterable
from .openai_utils import openai_system_user_prompt
from .openai_coder import OpenAICoder
from ..core.coder import Coder
from ..tests.python_tests import PythonTests


class PythonOpenAICoder(OpenAICoder):
    @property
    def default_config(self) -> dict[str, Any]:
        config = super().default_config.copy()

        config.update({
            "model": "gpt-4-turbo",
        })

        return config

    files_to_tests = PythonTests

    @property
    def subcoders(self) -> Iterable[Type[Coder]]:
        return (PythonOpenAICoder,)

    def design_solution(self, specification: Any) -> str:
        model_input = openai_system_user_prompt("You are an assistant that helps generate design documents. Your requirements are: \n1. Design a system that meets the following specification.\n2. You must use Python.\n3. You must specify all frameworks used. (e.g. This will be built in Django and will utilize OpenCV).\n4. Make sure to be extremely detailed.", specification)
        response = self.model(messages=model_input)
        return response.choices[0].message.content
