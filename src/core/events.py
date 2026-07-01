from datetime import datetime, timedelta
from typing import Any, List

from pydantic import BaseModel


class MessageMetaData(BaseModel):
    """
    States of the message that do no change as it goes through the AI system. Eventually this information is used to publish to the user.

    NOTE: tslr = time since last response


    Attributes:
    - platform_type: The platform type of the message (ie. discord_text, instagram_text, etc.)
    - user_id: ID of the user
    - channel_id: ID of the channel the content is being sent to     # TODO: Perhaps maybe input and output channel ids in future?
    - timestamp: timestamp of the last message
    - tslr_user_ai: Time between last user message to AI
    - tslr_ai_user: Time between last AI message to user
    - tslr_ai_ai: Time since last message from AI, ie. AI texting multiple times in same exchange
    """

    platform_type: str
    user_id: str
    channel_id: str
    timestamp: datetime
    tslr_user_ai: timedelta
    tslr_ai_user: timedelta
    tslr_ai_ai: timedelta


class AIMessage(BaseModel):
    """
    Message from the AI.

    Attributes:
    - content: The content of the message.
    - metadata: The metadata of the message.
    """

    content: str
    metadata: MessageMetaData


class UserMessage(BaseModel):
    """
    Message from the user.

    Attributes:
    - content: The content of the message.
    - user_name: The name of the user who sent the message.
    - metadata: The metadata of the message.
    """

    # NOTE: It would be a lot more robust if content was a list of messages rather than just a single string
    content: str
    ai_messages: List[Any]
    user_name: str
    metadata: MessageMetaData


class LLMInputMessage(BaseModel):
    """
    Message from the user that has passed through the behaviour layer.

    Attributes:
    - content: The content of the message.
    - user_name: The name of the user who sent the message.
    - metadata: The metadata of the message.
    """

    content: str
    user_name: str
    metadata: MessageMetaData
