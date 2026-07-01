import logging
from typing import Any, List

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

TURN_CONTROL_PROMPT = """
You are the turn detection module of an AI system. Your role is to check if it is the AI Agent's (Azaria's) turn to respond in a given conversation. You are given the AI's messages that the user is responding to and the user's response to the AI's last batch of messages. Return only the words "TRUE" or "FALSE"  referring to whether the user is done their part of the conversation and the AI should respond.
"""

logger = logging.getLogger("behaviour")


class LLMTurnControlModel:
    def __init__(self, model_path: str, base_model_name: str, **kwargs: Any) -> None:
        self._tokenizer = AutoTokenizer.from_pretrained(base_model_name)
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=quantization_config,
            device_map="auto",
        )

    def check_is_respond_turn(self, content: str, ai_messages: List[str]) -> bool:
        message_dicts = [
            {"role": "system", "content": TURN_CONTROL_PROMPT},
            {
                "role": "user",
                "content": f"user's messages:\n{content}\n\nai's messages:\n{ai_messages}\n",
            },
        ]
        prompt_text = self._tokenizer.apply_chat_template(
            message_dicts,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = self._tokenizer(prompt_text, return_tensors="pt").to(
            self._model.device
        )

        with torch.no_grad():
            output_ids = self._model.generate(
                **inputs, do_sample=False, max_new_tokens=100
            )

        new_tokens = output_ids[0][inputs["input_ids"].shape[1] :]
        response = self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        if response.upper() == "TRUE":
            logger.info(f"LLM Turn Control Responded True to: {content}")
            return True
        elif response.upper() == "FALSE":
            logger.info(f"LLM Turn Control Responded False to: {content}")
            return False
        else:
            logger.warning(
                f"Invalid response from LLM Turn Control, proceeding with Message Generation: {response}"
            )
            return True
