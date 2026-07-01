from __future__ import annotations

from typing import List

from behaviour.turn_control.turn_control_model import LLMTurnControlModel
from core.events import UserMessage


class TurnControl:
    """
    Detects whether or not it is the AI's turn to respond.

    Attributes:
    - model: model used to detect if it is the AI's turn to respond
    """

    def __init__(self):
        self.model = LLMTurnControlModel(
            model_path="Qwen/Qwen3.5-0.8B", base_model_name="Qwen/Qwen3.5-0.8B"
        )

    def check_is_respond_turn(self, message: UserMessage) -> bool:
        content = message.content
        ai_messages = message.ai_messages

        # TODO: this should pass in the content to some sort of language model which says whether or not its the AI's turn to respond
        # Pass the prompt and the text into the AI model
        # get the response of the model
        # then say true or false or something
        return self.model.check_is_respond_turn(content, ai_messages)
