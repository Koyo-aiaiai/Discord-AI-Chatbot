import json
import re
import uuid
from typing import Any, List, Optional, Sequence, Union

import torch
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables.base import RunnableBinding
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

_TOOL_CALL_PATTERN = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)


def _message_to_dict(message: BaseMessage) -> dict[str, Any]:
    """Convert a LangChain message into the dict format expected by Qwen chat templates."""
    if isinstance(message, SystemMessage):
        return {"role": "system", "content": message.content}
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": message.content}
    if isinstance(message, ToolMessage):
        return {
            "role": "tool",
            "content": message.content,
            "tool_call_id": message.tool_call_id,
        }
    if isinstance(message, AIMessage):
        msg: dict[str, Any] = {
            "role": "assistant",
            "content": message.content or "",
        }
        if message.tool_calls:
            msg["tool_calls"] = [
                {
                    "type": "function",
                    "id": tc.get("id", ""),
                    "function": {
                        "name": tc["name"],
                        "arguments": (
                            tc["args"]
                            if isinstance(tc["args"], str)
                            else json.dumps(tc["args"])
                        ),
                    },
                }
                for tc in message.tool_calls
            ]
        return msg
    role = message.type.replace("human", "user").replace("ai", "assistant")
    return {"role": role, "content": message.content}


def _parse_tool_calls(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Parse Qwen-style <tool_call> blocks into LangChain tool_calls."""
    tool_calls: list[dict[str, Any]] = []
    normal_parts: list[str] = []
    last_end = 0

    for match in _TOOL_CALL_PATTERN.finditer(text):
        normal_parts.append(text[last_end : match.start()])
        last_end = match.end()
        try:
            parsed = json.loads(match.group(1).strip())
            arguments = parsed.get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            tool_calls.append(
                {
                    "name": parsed["name"],
                    "args": arguments,
                    "id": f"call_{uuid.uuid4().hex}",
                    "type": "tool_call",
                }
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            continue

    normal_parts.append(text[last_end:])
    normal_text = "".join(normal_parts).strip()
    return normal_text, tool_calls


class HuggingFaceModel(BaseChatModel):
    """LangChain ChatModel with Huggingface Transformers as LLM"""

    _model_path: str
    _base_model_name: str
    _model: Any  # Some sort of LLM model
    _tokenizer: Any  # Some sort of tokenizer

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

        message_dicts = [_message_to_dict(m) for m in messages]

        tools = kwargs.get("tools", [])

        template_kwargs: dict[str, Any] = {
            "tokenize": False,
            "add_generation_prompt": True,
            "enable_thinking": False,
        }

        if tools:
            template_kwargs["tools"] = tools

        prompt_text = self._tokenizer.apply_chat_template(
            message_dicts,
            **template_kwargs,
        )

        inputs = self._tokenizer(prompt_text, max_length=4096, return_tensors="pt").to(
            self._model.device
        )

        with torch.no_grad():
            output_ids = self._model.generate(
                **inputs,
                temperature=config.get("temperature", 1.0),
                top_p=config.get("top_p", 0.95),
                repetition_penalty=config.get("repetition_penalty", 1.2),
                do_sample=config.get("do_sample", True),
                max_new_tokens=config.get("max_new_tokens", 1024),
            )

        new_tokens = output_ids[0][inputs["input_ids"].shape[1] :]
        response = self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        content, tool_calls = _parse_tool_calls(response)
        generation = ChatGeneration(
            message=AIMessage(
                content=content or ("" if tool_calls else response),
                tool_calls=tool_calls,
            )
        )

        return ChatResult(generations=[generation])

    def bind_tools(
        self,
        tools: Sequence[Union[BaseTool, dict]],
        *,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> RunnableBinding:
        formatted_tools = [convert_to_openai_tool(t) for t in tools]
        bind_kwargs = {"tools": formatted_tools, **kwargs}
        if tool_choice is not None:
            bind_kwargs["tool_choice"] = tool_choice
        return super().bind(**bind_kwargs)
