from typing import Any, List, Optional

import torch
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


class HuggingFaceModel(BaseChatModel):
    """LangChain ChatModel with Huggingface Transformers as LLM"""

    _model_path: str
    _base_model_name: str
    _model: Any # Some sort of LLM model
    _tokenizer: Any # Some sort of tokenizer

    def __init__(self, model_path: str, base_model_name: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._model_path = model_path
        self._base_model_name = base_model_name
        self._load_model()

    def _load_model(self) -> None:
        self._tokenizer = AutoTokenizer.from_pretrained(self._base_model_name)
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
        )

        self._model = AutoModelForCausalLM.from_pretrained(
            self._base_model_name,
            quantization_config=quantization_config,
            device_map="auto",
        )

        print("\033[1;35m [ Model loaded: Azaria is now Online! ] \033[0m")

    @property
    def _llm_type(self) -> str:
        return "transformers"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        config = {}
        if run_manager and hasattr(run_manager, "config"):
            config = run_manager.config.get("configurable", {})

        message_dicts = [
            {"role": m.type.replace("human", "user").replace("ai", "assistant"), "content": m.content} for m in messages
        ]

        prompt_text = self._tokenizer.apply_chat_template(
            message_dicts,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = self._tokenizer(prompt_text, max_length=4096, return_tensors="pt").to(self._model.device)

        with torch.no_grad():
            output_ids = self._model.generate(
                **inputs,
                temperature=config.get("temperature", 1.0),
                top_p=config.get("top_p", 0.95),
                repetition_penalty=config.get("repetition_penalty", 1.2),
                do_sample=config.get("do_sample", True),
                max_new_tokens=config.get("max_new_tokens", 100),
            )

        new_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
        response = self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        generation = ChatGeneration(message=AIMessage(content=response))

        return ChatResult(generations=[generation])
