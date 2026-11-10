import asyncio
import logging
import os

import httpx

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT = float(os.getenv("WEBHOOK_TIMEOUT", "10.0"))
WEBHOOK_MAX_RETRIES = int(os.getenv("WEBHOOK_MAX_RETRIES", "3"))
WEBHOOK_RETRY_DELAY = float(os.getenv("WEBHOOK_RETRY_DELAY", "1.0"))


async def send_webhook(url: str, payload: dict) -> bool:
    for attempt in range(WEBHOOK_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code < 300:
                    return True
                logger.warning(
                    "webhook %s status %d attempt %d",
                    url, resp.status_code, attempt + 1,
                )
        except httpx.HTTPError as e:
            logger.warning(
                "webhook %s error %s attempt %d", url, e, attempt + 1
            )
        if attempt < WEBHOOK_MAX_RETRIES - 1:
            await asyncio.sleep(WEBHOOK_RETRY_DELAY * (attempt + 1))
    return False
