from typing import Any
from models.wrapper import ModelWrapper
from openai import OpenAI


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
        self.default_generate_config = self.DEFAULT_CONFIG.copy()
        if default_generate_config is not None:
            self.default_generate_config.update(default_generate_config)
        
        self.client = OpenAI(
            organization=organization,
            apiKey=key,
        )

    def generate(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate text from the given input.
        """
        
        kwargs.update(self.default_generate_config)

        return self.client.chat.completions.create(**kwargs)
