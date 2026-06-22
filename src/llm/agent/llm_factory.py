import json
import os

from langchain_core.language_models.chat_models import BaseChatModel

from constants import ANSI
from llm.agent.huggingface_model import HuggingFaceModel

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")


class LLMFactory:
    def __init__(self):
        with open(CONFIG_PATH) as f:
            self.config = json.load(f)
        self.model_type = self.config["model_type"]
        self._config_dir = os.path.dirname(CONFIG_PATH)

    def _resolve_path(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        return os.path.join(self._config_dir, path)

    def make_model(self) -> BaseChatModel:
        """
        Makes a model based on the config.
        """
        match self.model_type:
            case "huggingface":
                return HuggingFaceModel(
                    model_path=self._resolve_path(self.config["model_name"]),
                    base_model_name=self.config["base_model_name"],
                )
            case _:
                raise ValueError(
                    f"{ANSI['LLM_DEBUG_COLOUR']}Unspported model type: {self.model_type}{ANSI['ANSI_RESET']}"
                )
