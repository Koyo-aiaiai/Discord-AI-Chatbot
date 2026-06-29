from datetime import datetime
from typing import Any, Union

import discord
from pydantic import BaseModel, ConfigDict


class DiscordMessage(BaseModel):
    """
    Abstraction for message from discord channel. Used cuz not a good idea to mutate discord.Message objects.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    content: str
    author: Union[Any, discord.User]
    channel: Union[Any, discord.TextChannel]
    created_at: datetime
