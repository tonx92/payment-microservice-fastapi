import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.outbox import Outbox
from api.models.payment import Payment
from api.schemas.payment import PaymentCreate


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_payment(
        self, data: PaymentCreate, idempotency_key: str
    ) -> tuple[Payment, bool]:
        existing = await self._get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing, False

        payment = Payment(
            id=uuid.uuid4(),
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            metadata_=data.metadata_,
            idempotency_key=idempotency_key,
            webhook_url=data.webhook_url,
        )
        self.db.add(payment)
        await self.db.flush()

        event = Outbox(
            event_type="payment.created",
            payload={"payment_id": str(payment.id)},
        )
        self.db.add(event)
        return payment, True

    async def get_payment(self, payment_id: uuid.UUID) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def _get_by_idempotency_key(self, key: str) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(Payment.idempotency_key == key)
        )
        return result.scalar_one_or_none()
