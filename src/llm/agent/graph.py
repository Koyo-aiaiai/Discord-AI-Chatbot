import logging
import uuid
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore
from langmem import (
    create_manage_memory_tool,
    create_memory_manager,
    create_search_memory_tool,
)

from constants import ANSI
from llm.agent.llm_factory import LLMFactory
from llm.agent.memory import MemoryStore
from llm.agent.prompts import memory_instructions, sys_prompt
from llm.agent.states import OverallState
from llm.agent.utils import LLMOutputValidationError, parse_llm_output
from llm.constants import MAX_RETRIES

logger = logging.getLogger(__name__)

llm_factory = LLMFactory()
model = llm_factory.make_model()
# memory_store = MemoryStore()
memory_store = InMemoryStore()
memory_manager = create_memory_manager(
    model,
    instructions=(memory_instructions),
    enable_inserts=True,
    enable_updates=True,
    enable_deletes=True,
)

_FALLBACK_MESSAGE = "I am going to fucking explode"


def build_context(state: OverallState) -> OverallState:
    return {
        "metadata": state["metadata"],
        "messages": state["messages"],
    }


def retrieve_memory(state: OverallState) -> OverallState:
    # TODO: This should eventually use semantic search
    user_id = state["user_name"]
    memory_context = memory_store.search(namespace=user_id, query="", limit=20)
    return {"memory_context": memory_context}


def generate_response(state: OverallState) -> OverallState:
    prompt = [SystemMessage(content=sys_prompt.strip())]
    if state.get("memory_context"):
        prompt.append(
            SystemMessage(
                content=f"Relevant memories about {state['user_name']}:\n{state['memory_context']}"
            )
        )
    prompt.extend(state["messages"])
    print(prompt)
    response = model.invoke(prompt)
    return {
        "metadata": state["metadata"],
        "messages": [response],
    }


def validate_response(state: OverallState) -> OverallState:
    """Validate the latest model output and retry with feedback when invalid."""
    last_message = state["messages"][-1]
    try:
        messages = parse_llm_output(last_message.content)
        return {"parsed_messages": messages}
    except LLMOutputValidationError as exc:
        retry_count = state.get("retry_count", 0) + 1
        if retry_count <= MAX_RETRIES:
            logger.warning(
                f"{ANSI['LLM_DEBUG_COLOUR']}LLM output validation failed (attempt {retry_count}/{MAX_RETRIES + 1}): {exc} \n\n Content: {last_message.content}{ANSI['ANSI_RESET']}"
            )
            return {
                "retry_count": retry_count,
                "messages": [
                    HumanMessage(
                        content=(
                            f"Your previous output was invalid: {exc}. "
                            'Respond with valid JSON containing a "messages" field '
                            "that is a list of non-empty strings."
                        )
                    )
                ],
            }

        logger.error(
            "LLM output validation failed after %d attempts, using fallback message",
            retry_count,
        )
        return {
            "retry_count": retry_count,
            "parsed_messages": [_FALLBACK_MESSAGE],
        }


def store_memory(state: OverallState) -> OverallState:
    namespace = state["user_name"]

    existing_items = memory_store.search(namespace=namespace, query="", limit=200)
    existing = [
        {"id": item.key, "content": item.value["content"]} for item in existing_items
    ]

    ops = memory_manager.invoke(
        {
            "messages": state["messages"],
            "existing": existing,
        }
    )

    for op in ops:
        op_type = op.get("type", "").lower()

        if op_type in ("insert", "update"):
            key = op.get("id") or str(uuid.uuid4())
            memory_store.put(namespace, key, {"content": op["content"]})
        elif op_type == "delete" and op.get("id"):
            memory_store.delete(namespace, op["id"])

    return {}


def route_after_validation(
    state: OverallState,
) -> Literal["generate_response", "store_memory"]:
    if state.get("parsed_messages"):
        return "store_memory"
    return "generate_response"


builder = StateGraph(OverallState)
builder.add_node("build_context", build_context)
builder.add_node("retrieve_memory", retrieve_memory)
builder.add_node("generate_response", generate_response)
builder.add_node("validate_response", validate_response)
builder.add_node("store_memory", store_memory)
builder.add_edge(START, "build_context")
builder.add_edge("build_context", "retrieve_memory")
builder.add_edge("retrieve_memory", "generate_response")
builder.add_edge("generate_response", "validate_response")
builder.add_conditional_edges(
    "validate_response",
    route_after_validation,
    {
        "generate_response": "generate_response",
        "store_memory": "store_memory",
    },
)
builder.add_edge("store_memory", END)
graph = builder.compile()
