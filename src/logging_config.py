import logging

from discord.utils import _ColourFormatter

ANSI = {
    "core": "\033[91m",
    "llm": "\033[94m",
    "adapter": "\033[95m",
    "behaviour": "\033[92m",
}


def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(
        _ColourFormatter("[%(levelname)s] %(colored_name)s: %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
