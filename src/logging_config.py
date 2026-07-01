import logging

ANSI = {
    "core": "\033[91m",
    "llm": "\033[94m",
    "adapter": "\033[95m",
    "behaviour": "\033[92m",
}

RESET = "\033[0m"


class ColourFormatter(logging.Formatter):
    def format(self, record):
        color = ANSI.get(record.name, "")

        record.colored_name = f"{color}{record.name}{RESET}"
        record.colored_message = f"{color}{record.getMessage()}{RESET}"

        return super().format(record)


def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(
        ColourFormatter("[%(levelname)s] %(colored_name)s: %(colored_message)s")
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
