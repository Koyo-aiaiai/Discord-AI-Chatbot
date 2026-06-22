import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from adapters.discord_bot.discord_service import DiscordService
from adapters.discord_bot.tests.discord_mocks import MockDiscordPlatform
from core.bus import EventBus
from core.events import AIMessage, MessageMetaData, UserMessage


@pytest.fixture
def mock_discord() -> MockDiscordPlatform:
    return MockDiscordPlatform()


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def discord_service(bus: EventBus) -> DiscordService:
    return DiscordService(bus)


async def test_read_message(
    mock_discord: MockDiscordPlatform,
    discord_service: DiscordService,
    bus: EventBus,
):
    """Inbound DM is packed as UserMessage and published to the event bus."""
    received: asyncio.Queue[UserMessage] = asyncio.Queue()
    bus.subscribe(UserMessage, received)

    message = mock_discord.incoming_dm("hello bot")
    await discord_service.handle_discord_message(message)

    published = await asyncio.wait_for(received.get(), timeout=1)
    assert published.content == "hello bot"
    assert published.user_name == "testuser"
    assert published.metadata.user_id == str(mock_discord.user_id)
    assert published.metadata.channel_id == str(mock_discord.channel_id)
    assert published.metadata.platform_type == "discord_text"
    assert published.metadata.tslr_user_ai == timedelta(0)


async def test_send_message(
    mock_discord: MockDiscordPlatform,
    discord_service: DiscordService,
    bus: EventBus,
):
    """AIMessage on the bus is delivered to the mock Discord channel."""
    mock_discord.attach_bot(discord_service)

    ai_message = AIMessage(
        content="hello user",
        metadata=MessageMetaData(
            platform_type="discord_text",
            user_id=str(mock_discord.user_id),
            channel_id=str(mock_discord.channel_id),
            timestamp=datetime.now(timezone.utc),
            tslr_user_ai=timedelta(0),
            tslr_ai_user=timedelta(0),
            tslr_ai_ai=timedelta(0),
        ),
    )

    worker = asyncio.create_task(discord_service._process_ai_messages())
    try:
        await bus.publish(ai_message)
        for _ in range(50):
            if mock_discord.sent_messages:
                break
            await asyncio.sleep(0)
        else:
            pytest.fail("AIMessage was not sent to the mock Discord channel")
    finally:
        worker.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker

    assert len(mock_discord.sent_messages) == 1
    assert mock_discord.sent_messages[0]["content"] == "hello user"
    assert mock_discord.sent_messages[0]["channel_id"] == str(mock_discord.channel_id)


async def test_tslr_user_ai_tracks_reply_delay(
    mock_discord: MockDiscordPlatform,
    discord_service: DiscordService,
):
    """tslr_user_ai reflects time since the AI's last outbound message."""
    mock_discord.attach_bot(discord_service)
    channel_id = str(mock_discord.channel_id)

    first_user_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    await discord_service.handle_discord_message(
        mock_discord.incoming_dm("first", created_at=first_user_at)
    )

    ai_at = first_user_at + timedelta(seconds=5)
    discord_service._record_ai_message(channel_id, ai_at)

    second_user_at = ai_at + timedelta(seconds=30)
    received: asyncio.Queue[UserMessage] = asyncio.Queue()
    discord_service.bus.subscribe(UserMessage, received)
    await discord_service.handle_discord_message(
        mock_discord.incoming_dm("second", created_at=second_user_at)
    )

    published = await asyncio.wait_for(received.get(), timeout=1)
    assert published.metadata.tslr_user_ai == timedelta(seconds=30)
    assert published.metadata.tslr_ai_user == timedelta(seconds=35)
