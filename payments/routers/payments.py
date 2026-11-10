import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from payments.database import get_db
from payments.schemas.payment import PaymentCreate, PaymentRead
from payments.services.payment_service import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


def _get_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    return PaymentService(db)


@router.post(
    "",
    response_model=PaymentRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_payment(
    body: PaymentCreate,
    idempotency_key: str = Header(
        ..., alias="Idempotency-Key", max_length=128, description="Unique idempotency key"
    ),
    service: PaymentService = Depends(_get_service),
):
    payment, _created = await service.create_payment(body, idempotency_key)
    return payment


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: uuid.UUID,
    service: PaymentService = Depends(_get_service),
):
    payment = await service.get_payment(payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment_id} not found",
        )
    return payment
