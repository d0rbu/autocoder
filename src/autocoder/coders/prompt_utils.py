from typing import Any


def system_prompt(system_prompt: str) -> dict[str, str]:
    """Returns a single message that is the system prompt.

    Args:
        system_prompt (str): The system prompt.

    Returns:
        dict[str, str]: A single message that is the system prompt.
    """
    return {
        "role": "system",
        "content": system_prompt,
    }


def assistant_prompt(assistant_prompt: str) -> dict[str, str]:
    """Returns a single message that is the assistant prompt.

    Args:
        assistant_prompt (str): The assistant prompt.

    Returns:
        dict[str, str]: A single message that is the assistant prompt.
    """
    return {
        "role": "assistant",
        "content": assistant_prompt,
    }


def user_prompt(user_prompt: str) -> dict[str, str]:
    """Returns a single message that is the user prompt.

    Args:
        user_prompt (str): The user prompt.

    Returns:
        dict[str, str]: A single message that is the user prompt.
    """
    return {
        "role": "user",
        "content": user_prompt,
    }


def system_user_prompt(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
    """Returns a single list that is the combination of the system prompt and the user prompt.

    Args:
        system_prompt (str): The system prompt.
        user_prompt (str): The user prompt.

    Returns:
        list[dict[str, str]]: A list that is the combination of the system prompt and the user prompt.
    """
    return [
        system_prompt(system_prompt),
        user_prompt(user_prompt),
    ]


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
