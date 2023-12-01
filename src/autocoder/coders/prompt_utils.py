import json
from typing import Any
from openai.types.chat import ChatCompletion


def system_prompt(prompt: str) -> dict[str, str]:
    """Returns a single message that is the system prompt.

    Args:
        prompt (str): The system prompt.

    Returns:
        dict[str, str]: A single message that is the system prompt.
    """
    return {
        "role": "system",
        "content": prompt,
    }


def assistant_prompt(prompt: str) -> dict[str, str]:
    """Returns a single message that is the assistant prompt.

    Args:
        prompt (str): The assistant prompt.

    Returns:
        dict[str, str]: A single message that is the assistant prompt.
    """
    return {
        "role": "assistant",
        "content": prompt,
    }


def user_prompt(prompt: str) -> dict[str, str]:
    """Returns a single message that is the user prompt.

    Args:
        prompt (str): The user prompt.

    Returns:
        dict[str, str]: A single message that is the user prompt.
    """
    return {
        "role": "user",
        "content": prompt,
    }


def system_user_prompt(system_message: str, user_message: str) -> list[dict[str, str]]:
    """Returns a single list that is the combination of the system prompt and the user prompt.

    Args:
        system_message (str): The system prompt.
        user_message (str): The user prompt.

    Returns:
        list[dict[str, str]]: A list that is the combination of the system prompt and the user prompt.
    """
    return [
        system_prompt(system_message),
        user_prompt(user_message),
    ]


def validate_openai_tool_usage(tool_usage: ChatCompletion) -> ChatCompletion:
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


def tool(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    """Returns a single tool.

    Args:
        name (str): The name of the tool.
        description (str): The description of the tool.
        parameters (dict[str, Any]): The parameters of the tool.

    Returns:
        dict[str, Any]: A single tool.
    """
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        }
    }

select_file_tool = tool(
    name="select_file",
    description="Select a file to write tests in. It may be a new file or an existing file.",
    parameters={
        "type": "object",
        "properties": {
            "file": {
                "type": "string",
            },
        },
        "required": ["file"],
    },
)

finish_tool = tool(
    name="finish",
    description="Signal that you are done.",
    parameters={
        "type": "object",
        "properties": {},
    },
)

code_writing_tools = [
    select_file_tool,
    finish_tool,
]
