import json
import logging
import os

from langchain_core.language_models.chat_models import BaseChatModel

from llm.agent.huggingface_model import HuggingFaceModel

logger = logging.getLogger("llm")


class LLMFactory:
    def __init__(self):
        self._config_dir = os.path.join(os.path.dirname(__file__), "..")

    def _resolve_path(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        return os.path.join(self._config_dir, path)

    def make_model(self, config_path: str) -> BaseChatModel:
        """
        Makes a model based on the config.
        """
        with open(config_path) as f:
            config = json.load(f)

        model_type = config["model_type"]
        model_name = config["model_name"]
        model_base = config["base_model_name"]

        model_name = self._resolve_path(model_name)

        match model_type:
            case "huggingface":
                return HuggingFaceModel(
                    model_path=model_name,
                    base_model_name=model_base,
                )
            case _:
                logger.error(f"Unspported model type: {model_type}")
                raise ValueError(f"Unspported model type: {model_type}")
