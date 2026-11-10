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
WORKER_MAX_ATTEMPTS = int(os.getenv("WORKER_MAX_ATTEMPTS", "3"))
QUEUE_NAME = "payments"
EXCHANGE_NAME = "payments"
DLX_NAME = "payments_dlx"
DLQ_NAME = "payments_dlq"


async def setup_queues(connection: aio_pika.abc.AbstractConnection) -> None:
    channel = await connection.channel()
    await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT)
    await channel.declare_exchange(DLX_NAME, aio_pika.ExchangeType.DIRECT)
    await channel.declare_queue(DLQ_NAME, durable=True)
    await channel.declare_queue(
        QUEUE_NAME, durable=True,
        arguments={
            "x-dead-letter-exchange": DLX_NAME,
            "x-dead-letter-routing-key": DLQ_NAME,
        },
    )
    await channel.queue_bind(QUEUE_NAME, EXCHANGE_NAME, QUEUE_NAME)
    await channel.queue_bind(DLQ_NAME, DLX_NAME, DLQ_NAME)


async def process_payment(
    message: aio_pika.abc.AbstractIncomingMessage,
    channel: aio_pika.abc.AbstractChannel,
) -> None:
    body = json.loads(message.body)
    payment_id = uuid.UUID(body["payment_id"])
    attempts = body.get("attempts", 1)

    async with async_session_factory() as session:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            await message.nack(requeue=False)
            return

        await asyncio.sleep(random.uniform(2.0, 5.0))
        success = random.random() < 0.9

        if success:
            payment.status = PaymentStatus.SUCCEEDED
            payment.processed_at = datetime.now(timezone.utc)
            await session.commit()

            if payment.webhook_url:
                payload = {
                    "payment_id": str(payment.id),
                    "status": payment.status.value,
                    "amount": str(payment.amount),
                    "currency": payment.currency.value,
                }
                await send_webhook(payment.webhook_url, payload)
            await message.ack()
        else:
            if attempts >= WORKER_MAX_ATTEMPTS:
                payment.status = PaymentStatus.FAILED
                payment.processed_at = datetime.now(timezone.utc)
                await session.commit()
                await message.nack(requeue=False)
            else:
                await session.rollback()
                new_body = json.dumps({**body, "attempts": attempts + 1})
                await channel.basic_publish(
                    aio_pika.Message(body=new_body.encode()),
                    exchange=EXCHANGE_NAME,
                    routing_key=QUEUE_NAME,
                )
                await message.ack()


async def start_worker(shutdown_event: asyncio.Event) -> None:
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    await setup_queues(connection)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    queue = await channel.get_queue(QUEUE_NAME)

    try:
        async with queue.iter(no_ack=False) as exc:
            async for message in exc:
                if shutdown_event.is_set():
                    break
                try:
                    await process_payment(message, channel)
                except Exception:
                    logger.exception("unhandled error processing message")
                    await message.nack(requeue=False)
    finally:
        await connection.close()
        logger.info("worker stopped")
