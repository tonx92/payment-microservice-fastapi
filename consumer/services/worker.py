import asyncio
import json
import logging
import os
import random
import uuid
from datetime import datetime, timezone

import aio_pika
from sqlalchemy import delete, select

from consumer.database import async_session_factory
from consumer.models.outbox import Outbox
from consumer.models.payment import Payment, PaymentStatus
from consumer.services.webhook import send_webhook

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
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


async def _send_webhook(
    payment: Payment,
    message: aio_pika.abc.AbstractIncomingMessage,
) -> None:
    if not payment.webhook_url:
        await message.ack()
        return

    payload = {
        "payment_id": str(payment.id),
        "status": payment.status.value,
        "amount": str(payment.amount),
        "currency": payment.currency.value,
    }
    delivered = await send_webhook(payment.webhook_url, payload)
    if delivered:
        await message.ack()
    else:
        await message.nack(requeue=False)


async def process_payment(
    message: aio_pika.abc.AbstractIncomingMessage,
) -> None:
    body = json.loads(message.body)
    payment_id = uuid.UUID(body["payment_id"])

    async with async_session_factory() as session:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            await message.nack(requeue=False)
            return

        if payment.status not in (PaymentStatus.SUCCEEDED, PaymentStatus.FAILED):
            await asyncio.sleep(random.uniform(2.0, 5.0))
            success = random.random() < 0.9

            if success:
                payment.status = PaymentStatus.SUCCEEDED
            else:
                payment.status = PaymentStatus.FAILED

            payment.processed_at = datetime.now(timezone.utc)

            await session.execute(
                delete(Outbox).where(
                    Outbox.payment_id == payment.id,
                    Outbox.event_type == "payment.created",
                )
            )
            await session.commit()

        if payment.status == PaymentStatus.SUCCEEDED:
            await _send_webhook(payment, message)
        else:
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

    try:
        while not shutdown_event.is_set():
            try:
                message = await queue.get(no_ack=False)
            except aio_pika.exceptions.QueueEmpty:
                await asyncio.sleep(1)
                continue
            try:
                await process_payment(message)
            except Exception:
                logger.exception("unhandled error processing message")
                await message.nack(requeue=False)
    finally:
        await connection.close()
        logger.info("worker stopped")
