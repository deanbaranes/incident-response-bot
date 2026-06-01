import os
import sys
import json
import asyncio
import logging
import signal
from aiokafka import AIOKafkaConsumer  # type: ignore
from cachetools import TTLCache
from prometheus_client import start_http_server, Counter

# Add project root to sys.path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_INCIDENT_TOPIC,
    KAFKA_CONSUMER_GROUP,
    KAFKA_DLQ_TOPIC,
    USE_KAFKA_QUEUE,
)
from core.engine import process_incident
from core.log_config import setup_logging, incident_id_var
from aiokafka.producer import AIOKafkaProducer  # type: ignore

setup_logging()
logger = logging.getLogger("incident_consumer")

# Prometheus Metrics
MESSAGES_PROCESSED = Counter(
    "incident_bot_messages_processed_total",
    "Total number of messages processed successfully",
)
DLQ_MESSAGES = Counter(
    "incident_bot_dlq_messages_total", "Total number of messages sent to DLQ"
)

is_running = True


def handle_shutdown(sig, frame):
    global is_running
    logger.info("Received termination signal. Starting graceful shutdown...")
    is_running = False


# Simple in-memory LRU cache for idempotency with 1-hour TTL
# Prevents memory leak by capping size to 10,000 items
MAX_CACHE_SIZE = 10000
processed_incidents: TTLCache = TTLCache(maxsize=MAX_CACHE_SIZE, ttl=3600)


async def send_to_dlq(producer, message_value, error_msg):
    try:
        # Use Kafka Headers for DLQ exception traces as per Phase 5 spec
        headers = [("error", str(error_msg).encode("utf-8"))]
        await producer.send_and_wait(
            topic=KAFKA_DLQ_TOPIC, value=message_value, headers=headers
        )
        DLQ_MESSAGES.inc()
        logger.info("Sent failed message to DLQ.")
    except Exception as e:
        logger.error(f"Failed to send to DLQ: {e}")


async def consume():
    if not USE_KAFKA_QUEUE:
        logger.error("USE_KAFKA_QUEUE is false, but consumer was started. Exiting.")
        return

    logger.info(f"Starting Kafka Consumer for topic: {KAFKA_INCIDENT_TOPIC}")

    # Start Prometheus metrics server on port 8000 for the worker container
    try:
        start_http_server(8000)
        logger.info("Prometheus metrics server started on port 8000")
    except Exception as e:
        logger.warning(f"Could not start Prometheus metrics server: {e}")

    consumer = AIOKafkaConsumer(
        KAFKA_INCIDENT_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_CONSUMER_GROUP,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )

    dlq_producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

    await consumer.start()
    await dlq_producer.start()

    # Register signal handlers for graceful shutdown
    try:
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
    except NotImplementedError:
        pass  # Windows might not support all signals

    try:
        async for msg in consumer:
            if not is_running:
                logger.info("Shutdown requested. Breaking consumer loop gracefully...")
                break

            logger.info(
                f"Received message from partition {msg.partition} at offset {msg.offset}"
            )
            try:
                payload = json.loads(msg.value.decode("utf-8"))
                incident_id = payload.get("incident_id")

                if incident_id:
                    incident_id_var.set(incident_id)

                if incident_id and incident_id in processed_incidents:
                    logger.warning(
                        f"Incident {incident_id} already processed. Skipping (Idempotent)."
                    )
                    await consumer.commit()
                    continue

                # Await the async process_incident
                await process_incident(payload, incident_id)

                if incident_id:
                    processed_incidents[incident_id] = True

                # Commit only on success
                await consumer.commit()
                MESSAGES_PROCESSED.inc()
                logger.info(f"Successfully processed and committed offset {msg.offset}")

            except Exception as e:
                logger.error(f"Error processing message at offset {msg.offset}: {e}")
                await send_to_dlq(dlq_producer, msg.value, e)
                # Commit offset even on error to avoid poison message loops (since it's in DLQ)
                await consumer.commit()

    except asyncio.CancelledError:
        logger.info("Consumer task cancelled.")
    finally:
        await consumer.stop()
        await dlq_producer.stop()
        logger.info("Kafka Consumer stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        logger.info("Shutdown requested.")
