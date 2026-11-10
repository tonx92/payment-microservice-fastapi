from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from payments.database import engine
from payments.models.base import Base
from payments.routers import payments_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Payments Service", version="1.0.0", lifespan=lifespan)

app.include_router(payments_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}

