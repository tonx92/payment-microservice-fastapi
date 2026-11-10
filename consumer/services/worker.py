import asyncio
import json
import logging
import os
import random
import uuid
from datetime import datetime, timezone

import aio_pika

from consumer.database import async_session_factory
from consumer.models.payment import Payment, PaymentStatus
from consumer.services.webhook import send_webhook

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
CONSUMER_WORKER_MAX_ATTEMPTS = int(os.getenv("CONSUMER_WORKER_MAX_ATTEMPTS", "3"))
QUEUE_NAME = "payments"
EXCHANGE_NAME = "payments"
DLX_NAME = "payments_dlx"
DLQ_NAME = "payments_dlq"


async def setup_queues(connection: aio_pika.abc.AbstractConnection) -> None:
    channel = await connection.channel()
    await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT)
    await channel.declare_exchange(DLX_NAME, aio_pika.ExchangeType.DIRECT)
    await channel.declare_queue(DLQ_NAME, durable=True)
    queue = await channel.declare_queue(
        QUEUE_NAME, durable=True,
        arguments={
            "x-dead-letter-exchange": DLX_NAME,
            "x-dead-letter-routing-key": DLQ_NAME,
        },
    )
    dlq = await channel.get_queue(DLQ_NAME)
    await queue.bind(EXCHANGE_NAME, QUEUE_NAME)
    await dlq.bind(DLX_NAME, DLQ_NAME)


async def process_payment(
    message: aio_pika.abc.AbstractIncomingMessage,
    exchange: aio_pika.abc.AbstractExchange,
) -> None:
    body = json.loads(message.body)
    payment_id = uuid.UUID(body["payment_id"])
    attempts = body.get("attempts", 1)

    async with async_session_factory() as session:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            await message.nack(requeue=False)
            return

        if payment.webhook_url:
            payload = {
                "payment_id": str(payment.id),
                "status": payment.status.value,
                "amount": str(payment.amount),
                "currency": payment.currency.value,
            }
            await asyncio.sleep(random.uniform(2.0, 5.0))

            delivered = await send_webhook(payment.webhook_url, payload)
            if not delivered:
                if attempts >= CONSUMER_WORKER_MAX_ATTEMPTS:
                    await message.nack(requeue=False)
                    return
                await exchange.publish(
                    aio_pika.Message(body=json.dumps({**body, "attempts": attempts + 1}).encode()),
                    routing_key=QUEUE_NAME,
                )
                await message.ack()
                return
            payment.status = PaymentStatus.SUCCEEDED
            payment.processed_at = datetime.now(timezone.utc)
            await session.commit()
        await message.ack()


async def start_worker(shutdown_event: asyncio.Event) -> None:
    connection = None
    while connection is None:
        try:
            connection = await aio_pika.connect(RABBITMQ_URL)
        except Exception:
            logger.warning("rabbitmq not ready, retrying in 5s")
            await asyncio.sleep(5)
    logger.info("rabbitmq connected")
    await setup_queues(connection)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    queue = await channel.get_queue(QUEUE_NAME)
    exchange = await channel.get_exchange(EXCHANGE_NAME)

    try:
        while not shutdown_event.is_set():
            try:
                message = await queue.get(no_ack=False)
            except aio_pika.exceptions.QueueEmpty:
                await asyncio.sleep(1)
                continue
            try:
                await process_payment(message, exchange)
            except Exception:
                logger.exception("unhandled error processing message")
                await message.nack(requeue=False)
    finally:
        await connection.close()
        logger.info("worker stopped")
