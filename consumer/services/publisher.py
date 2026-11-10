import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import aio_pika
from sqlalchemy import select

from consumer.database import async_session_factory
from consumer.models.outbox import Outbox

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
PUBLISHER_POLL_INTERVAL = float(os.getenv("PUBLISHER_POLL_INTERVAL", "2.0"))
PUBLISHER_BATCH_SIZE = int(os.getenv("PUBLISHER_BATCH_SIZE", "50"))


async def publish_outbox_events(channel: aio_pika.abc.AbstractChannel) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Outbox).where(Outbox.published_at.is_(None)).limit(PUBLISHER_BATCH_SIZE)
        )
        events = result.scalars().all()
        if not events:
            return

        for event in events:
            await channel.basic_publish(
                aio_pika.Message(
                    body=json.dumps(event.payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                exchange="payments",
                routing_key="payments",
            )
            event.published_at = datetime.now(timezone.utc)

        await session.commit()
        logger.info("published %d outbox events", len(events))


async def start_publisher(shutdown_event: asyncio.Event) -> None:
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    await channel.declare_exchange("payments", aio_pika.ExchangeType.DIRECT)

    try:
        while not shutdown_event.is_set():
            try:
                await publish_outbox_events(channel)
            except Exception:
                logger.exception("outbox publish error")
            await asyncio.sleep(PUBLISHER_POLL_INTERVAL)
    finally:
        await connection.close()
        logger.info("publisher stopped")
