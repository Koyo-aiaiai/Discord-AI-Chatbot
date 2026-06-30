import logging
import os
import time
import warnings
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import OpenAIEmbeddings
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.postgres import PostgresStore
from langmem import (
    create_memory_store_manager,
)
from psycopg import Connection
from psycopg.rows import dict_row

from llm.agent.llm_factory import LLMFactory
from llm.agent.prompts import memory_instructions, sys_prompt
from llm.agent.states import OverallState
from llm.agent.utils import LLMOutputValidationError, parse_llm_output
from llm.constants import MAX_RETRIES

warnings.filterwarnings("ignore", category=FutureWarning)

DATABASE_URL = "postgresql://agent:fishfosh@localhost:5432/agent_memory"
PERSONALITY_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "personality_model_config.json"
)
MEMORY_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "memory_model_config.json"
)

load_dotenv()

logger = logging.getLogger(__name__)

_FALLBACK_MESSAGE = "I am going to fucking explode"
EMBEDDINGS_DIM = 1536


def build_context(state: OverallState) -> OverallState:
    return {
        "metadata": state["metadata"],
        "messages": state["messages"],
    }


def retrieve_memory(state: OverallState) -> OverallState:
    user_message = state["messages"][-1].content
    lr_memory_context = memory_manager.search(
        query=user_message,
        config={
            "configurable": {
                "user_id": state["metadata"].user_id,
                "channel_id": state["metadata"].channel_id,
            },
            "limit": 20,
        },
    )
    # print(f"LR Memory context: {lr_memory_context}")
    return {
        "lr_memory_context": lr_memory_context,
    }


def generate_response(state: OverallState) -> OverallState:
    start_time = time.time()
    prompt = [SystemMessage(content=sys_prompt.strip())]
    if state.get("lr_memory_context"):
        prompt.append(
            SystemMessage(
                content=f"Relevant facts and memories about {state['user_name']}:\n{state['lr_memory_context']}"
            )
        )
    prompt.extend(state["messages"][-10:])
    logger.info(f"Prompt: {prompt}")
    response = personality_model.invoke(prompt)
    end_time = time.time()
    latency = end_time - start_time
    logger.info(f"Model Generation Latency: {latency}")
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
                f"LLM output validation failed (attempt {retry_count}/{MAX_RETRIES + 1}): {exc} \n\n Content: {last_message.content}"
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
            f"LLM output validation failed after {retry_count} attempts, using fallback message"
        )
        return {
            "retry_count": retry_count,
            "parsed_messages": [_FALLBACK_MESSAGE],
        }


# FIXME: Figure out what is causing the massive latency in this
def store_memory(state: OverallState) -> OverallState:
    start_time = time.time()
    to_process = {
        "messages": [
            # FIXME: If there is need to retry, this will add the retry message rather than the user's message
            {"role": "user", "content": state["messages"][-2].content},
        ]
        + [
            {"role": "assistant", "content": message}
            for message in state["parsed_messages"]
        ],
    }
    memory_manager.invoke(
        input=to_process,
        config={
            "configurable": {
                "user_id": state["metadata"].user_id,
                "channel_id": state["metadata"].channel_id,
            },
            "recursion_limit": 10,
        },
    )
    end_time = time.time()
    latency = end_time - start_time
    logger.info(f"Memory Storage Latency: {latency}")

    return {}


def route_after_validation(
    state: OverallState,
) -> Literal["generate_response", "store_memory"]:
    if state.get("parsed_messages"):
        return "store_memory"
    return "generate_response"


llm_factory = LLMFactory()
personality_model = llm_factory.make_model(PERSONALITY_MODEL_PATH)
memory_model = llm_factory.make_model(MEMORY_MODEL_PATH)
print("\033[1;35m [ Azaria is now Online! ] \033[0m")

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

conn = Connection.connect(
    DATABASE_URL,
    autocommit=True,
    prepare_threshold=0,
    row_factory=dict_row,
)

memory_checkpointer = InMemorySaver()
memory_store = PostgresStore(
    conn,
    index={"dims": EMBEDDINGS_DIM, "embed": embeddings},
)

# NOTE: THIS IS FOR FIRST RUN TO SETUP POSTGRES VECTOR DB
# memory_store.setup()


memory_manager = create_memory_store_manager(
    memory_model,
    namespace=("memories", "{channel_id}", "{user_id}"),
    instructions=(memory_instructions),
    enable_inserts=True,
    enable_deletes=True,
)

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
graph = builder.compile(store=memory_store, checkpointer=memory_checkpointer)
