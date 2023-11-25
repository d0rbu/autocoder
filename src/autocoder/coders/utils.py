


def system_user_prompt(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
    """Returns a single list that is the combination of the system prompt and the user prompt.

    Args:
        system_prompt (str): The system prompt.
        user_prompt (str): The user prompt.

    Returns:
        list[dict[str, str]]: A list that is the combination of the system prompt and the user prompt.
    """
    return [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
        }
    ]