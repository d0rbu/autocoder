import os
import re
from typing import List, Tuple


DEFAULT_PERMISSIONS = 0o770
TRUNCATE_MESSAGE = "... (truncated)"


def get_exe_extension():
    if os.name == "nt":
        return ".exe"

    return ""


def truncate_chat(chat: str, chat_length: int = 256) -> str:
    """
    Truncates a chat to the given length.

    Args:
        chat (str): The chat to truncate.
        chat_length (int): The length to truncate the chat to.
    
    Returns:
        str: The truncated chat.
    """
    if len(chat) <= chat_length:
        return chat

    return chat[:chat_length - len(TRUNCATE_MESSAGE)] + TRUNCATE_MESSAGE


def parse_chat(chat: str) -> List[Tuple[str, str]]:
    """
    Extracts all code blocks from a chat and returns them as a list of (filename, codeblock) tuples.
    https://github.com/AntonOsika/gpt-engineer/blob/ed2f9d818b37b64515c08b5417763a98620933f2/gpt_engineer/core/chat_to_files.py
    
    Args:
        chat (str): The chat to parse.

    Returns:
        List[Tuple[str, str]]: A list of (filename, codeblock) tuples.
    """
    # Get all ``` blocks and preceding filenames
    regex = r"(\S+)\n?\s*```[^\n]*\n(.+?)\n*```"
    matches = re.finditer(regex, chat, re.DOTALL)

    files = []
    for match in matches:
        # Strip the filename of any non-allowed characters and convert / to \
        path = re.sub(r'[\:<>"|?*]', "", match.group(1))

        # Remove leading and trailing brackets
        path = re.sub(r"^\[(.*)\]$", r"\1", path)

        # Remove leading and trailing backticks
        path = re.sub(r"^`(.*)`$", r"\1", path)

        # Remove trailing ]
        path = re.sub(r"[\]\:]$", "", path)

        # Get the code
        code = match.group(2)

        # Add the file to the list
        files.append((path, code))

    # Return the files
    return files
