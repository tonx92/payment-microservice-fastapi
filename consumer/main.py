import asyncio
import logging
import signal

from consumer.services.publisher import start_publisher
from consumer.services.worker import start_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logging.getLogger("aiormq.connection").setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)


async def main() -> None:
    shutdown_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_event.set)

    await asyncio.gather(
        start_publisher(shutdown_event),
        start_worker(shutdown_event),
    )
    logger.info("consumer shut down")


if __name__ == "__main__":
    asyncio.run(main())
