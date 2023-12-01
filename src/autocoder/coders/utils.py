import os


def get_exe_extension():
    if os.name == "nt":
        return ".exe"

    return ""
