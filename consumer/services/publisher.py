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
CONSUMER_PUBLISHER_POLL_INTERVAL = float(os.getenv("CONSUMER_PUBLISHER_POLL_INTERVAL", "2.0"))
CONSUMER_PUBLISHER_BATCH_SIZE = int(os.getenv("CONSUMER_PUBLISHER_BATCH_SIZE", "50"))


async def publish_outbox_events(exchange: aio_pika.abc.AbstractExchange) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Outbox).where(Outbox.published_at.is_(None)).limit(CONSUMER_PUBLISHER_BATCH_SIZE)
        )
        events = result.scalars().all()
        if not events:
            return

        for event in events:
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(event.payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key="payments",
            )
            event.published_at = datetime.now(timezone.utc)

        await session.commit()
        logger.info("published %d outbox events", len(events))


async def start_publisher(shutdown_event: asyncio.Event) -> None:
    connection = None
    while connection is None:
        try:
            connection = await aio_pika.connect(RABBITMQ_URL)
        except Exception:
            logger.warning("rabbitmq not ready, retrying in 5s")
            await asyncio.sleep(5)
    logger.info("rabbitmq connected")
    channel = await connection.channel()
    exchange = await channel.declare_exchange("payments", aio_pika.ExchangeType.DIRECT)

    try:
        while not shutdown_event.is_set():
            try:
                await publish_outbox_events(exchange)
            except Exception:
                logger.exception("outbox publish error")
            await asyncio.sleep(CONSUMER_PUBLISHER_POLL_INTERVAL)
    finally:
        await connection.close()
        logger.info("publisher stopped")
