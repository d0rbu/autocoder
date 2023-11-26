from typing import Any
from openai import OpenAI
from .wrapper import ModelWrapper


class OpenAIWrapper(ModelWrapper):
    """
    OpenAI wrapper
    """

    DEFAULT_CONFIG = {
        "model": "gpt-3.5-turbo",
        "temperature": 0.1,
        "max_tokens": 2048,
        "top_p": 0.3,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "logit_bias": None,
        "n": 1,
        "response_format": { "type": "text" },
        "seed": 0,
        "stop": None,
        "stream": False,
        "tools": None,
        "tool_choice": None,
    }

    def __init__(self, key: str, organization: str | None = None, **default_generate_config: dict[str, Any]):
        super().__init__(default_generate_config)
        
        self.client = OpenAI(
            organization=organization,
            api_key=key,
        )

    def generate(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate text from the given input.
        """
        
        generate_config = self.default_generate_config.copy()
        generate_config.update(kwargs)

        return self.client.chat.completions.create(**generate_config)
