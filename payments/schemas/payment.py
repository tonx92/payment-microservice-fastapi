"""Payment Pydantic schemas for API request/response."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from payments.models.payment import Currency, PaymentStatus


class PaymentCreate(BaseModel):
    """Schema for creating a new payment."""

    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: Currency = Field(default=Currency.RUB, description="Currency code")
    description: str = Field(default="", max_length=500, description="Payment description")
    metadata_: dict | None = Field(default=None, alias="metadata", description="Additional metadata")
    idempotency_key: str = Field(..., max_length=128, description="Unique idempotency key")
    webhook_url: str | None = Field(default=None, max_length=1024, description="Webhook callback URL")

    model_config = ConfigDict(populate_by_name=True)


class PaymentRead(BaseModel):
    """Schema for reading a payment."""

    id: uuid.UUID
    amount: Decimal
    currency: Currency
    description: str
    metadata_: dict | None = Field(default=None, alias="metadata")
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str | None
    created_at: datetime
    processed_at: datetime | None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
