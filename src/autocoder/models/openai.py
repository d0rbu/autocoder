import time
import json
from collections import deque
from typing import Any
from openai import OpenAI
from openai.types.chat import ChatCompletion
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
        # "logit_bias": None,
        "n": 1,
        "response_format": { "type": "text" },
        "seed": 0,
        # "stop": None,
        "stream": False,
        # "tools": None,
        # "tool_choice": None,
    }

    SECONDS_PER_MINUTE = 60
    WAIT_EPSILON = 0.05

    def __init__(self, key: str, organization: str | None = None, rate_limit_rpm: int = 500, **default_generate_config: dict[str, Any]) -> None:
        super().__init__(**default_generate_config)
        
        self.client = OpenAI(
            organization=organization,
            api_key=key,
        )
        self.rate_limit_rpm = rate_limit_rpm  # rate limit is in requests per minute
        self.last_request_times = deque((0,), maxlen=self.rate_limit_rpm)
    
    def process_response(self, response: str) -> str:
        return self.validate_tool_usage(response)

    @staticmethod
    def validate_tool_usage(tool_usage: ChatCompletion) -> ChatCompletion:
        """Validates that the tool usage is valid, if any tool is used.

        Args:
            tool_usage (ChatCompletion): The chat completion that may contain tool usage.

        Raises:
            ValueError: If the tool usage is invalid.

        Returns:
            ChatCompletion: The same chat completion.
        """
        for choice in tool_usage.choices:
            if not choice.message.tool_calls:
                continue

            for tool_call in choice.message.tool_calls:
                arguments = tool_call.function.arguments
                arguments = json.loads(arguments)
                tool_call.function.arguments = arguments

        return tool_usage

    def generate(
        self,
        model_input: Any,
        **kwargs: Any,
    ) -> ChatCompletion:
        generate_config = self.default_generate_config.copy()
        generate_config.update(kwargs)

        one_minute_ago = time.time() - self.SECONDS_PER_MINUTE
        if self.last_request_times[0] > one_minute_ago:
            time_left = self.last_request_times[0] - one_minute_ago
            time.sleep(time_left + self.WAIT_EPSILON)
        
        self.last_request_times.append(time.time())

        response = self.client.chat.completions.create(messages=model_input, **generate_config)

        print(response)

        return response
