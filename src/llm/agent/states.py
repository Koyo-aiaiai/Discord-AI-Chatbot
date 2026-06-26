from __future__ import annotations

from typing import Annotated, Dict, NotRequired, TypedDict

from langgraph.graph import add_messages

from core.events import MessageMetaData


class OverallState(TypedDict):
    metadata: MessageMetaData
    user_name: str
    messages: Annotated[list, add_messages]
    retry_count: NotRequired[int]
    parsed_messages: NotRequired[list[str]]
    lr_memory_context: NotRequired[str]
