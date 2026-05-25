import os
import sys
import json
import asyncio
import logging
from aiokafka import AIOKafkaConsumer  # type: ignore
from typing import Set

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
from core.log_config import setup_logging
from aiokafka.producer import AIOKafkaProducer  # type: ignore

setup_logging()
logger = logging.getLogger("incident_consumer")

# Simple in-memory cache for idempotency
# In a real distributed system, use Redis or Memcached
processed_incidents: Set[str] = set()


async def send_to_dlq(producer, message_value, error_msg):
    try:
        # Inject error message into the payload for debugging
        try:
            dlq_payload = json.loads(message_value)
            dlq_payload["_dlq_error"] = str(error_msg)
            payload_bytes = json.dumps(dlq_payload).encode("utf-8")
        except json.JSONDecodeError:
            # If it's not even valid JSON
            payload_bytes = message_value

        await producer.send_and_wait(topic=KAFKA_DLQ_TOPIC, value=payload_bytes)
        logger.info("Sent failed message to DLQ.")
    except Exception as e:
        logger.error(f"Failed to send to DLQ: {e}")


async def consume():
    if not USE_KAFKA_QUEUE:
        logger.error("USE_KAFKA_QUEUE is false, but consumer was started. Exiting.")
        return

    logger.info(f"Starting Kafka Consumer for topic: {KAFKA_INCIDENT_TOPIC}")

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

    try:
        async for msg in consumer:
            logger.info(
                f"Received message from partition {msg.partition} at offset {msg.offset}"
            )
            try:
                payload = json.loads(msg.value.decode("utf-8"))
                incident_id = payload.get("incident_id")

                if incident_id and incident_id in processed_incidents:
                    logger.warning(
                        f"Incident {incident_id} already processed. Skipping (Idempotent)."
                    )
                    await consumer.commit()
                    continue

                # Await the async process_incident
                await process_incident(payload, incident_id)

                if incident_id:
                    processed_incidents.add(incident_id)

                # Commit only on success
                await consumer.commit()
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
