import json

from langchain_core.messages import AIMessage as LangChainAIMessage
from langchain_core.messages import HumanMessage

from core.events import AIMessage, LLMInputMessage, MessageMetaData


class LLMOutputValidationError(ValueError):
    """Raised when LLM output does not match the expected JSON message format."""


def llm_input_to_langchain(message: LLMInputMessage) -> HumanMessage:
    """Convert a behaviour-layer event into a LangChain human message for the graph."""
    return HumanMessage(content=message.content, name=message.user_name)


def langchain_to_ai_message(
    message: LangChainAIMessage,
    metadata: MessageMetaData,
) -> AIMessage:
    """Convert a LangChain AI message back into a bus event."""
    return AIMessage(content=message.content, metadata=metadata)


def parse_llm_output(content: str) -> list[str]:
    """
    Parse and validate LLM JSON output into a list of message strings.

    Preconditions:
    - content is the raw text returned by the model.

    Raises:
    - LLMOutputValidationError: if the output is not valid JSON or does not
      contain a non-empty "messages" list of non-empty strings.
    """
    text = content.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMOutputValidationError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise LLMOutputValidationError("Output must be a JSON object")

    if "messages" not in data:
        raise LLMOutputValidationError('Missing required field "messages"')

    messages = data["messages"]
    if not isinstance(messages, list):
        raise LLMOutputValidationError('"messages" must be a list')

    if not messages:
        raise LLMOutputValidationError('"messages" must not be empty')

    for index, message in enumerate(messages):
        if not isinstance(message, str):
            raise LLMOutputValidationError(f'"messages[{index}]" must be a string')
        if not message.strip():
            raise LLMOutputValidationError(f'"messages[{index}]" must not be empty')

    return messages
