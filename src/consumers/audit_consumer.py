"""
Audit consumer — subscribes to the 'audit-events' Redpanda topic.

Persists every event to the audit_logs table via audit_service.record_event().
Retry policy: up to 3 attempts per message, 1-second sleep between retries.
After 3 failures: logs a dead-letter error and commits the offset to avoid loops.

Crash-safety guarantees:
  - Malformed messages are logged and skipped (offset committed)
  - Graceful shutdown on asyncio.CancelledError
  - Consumer loop never raises unhandled exceptions
"""
import asyncio
import json
import logging

from src.services.audit_service import record_event

logger = logging.getLogger(__name__)

TOPIC = "audit-events"
GROUP_ID = "audit-consumer-group"
MAX_RETRIES = 3


async def run_audit_consumer() -> None:
    """
    Long-running background task that consumes from the 'audit-events' topic
    and persists each event to the audit_logs table.
    Exits cleanly when cancelled. Logs a warning if Redpanda is unreachable.
    """
    try:
        from aiokafka import AIOKafkaConsumer
        from aiokafka.helpers import create_ssl_context
        from src.config import settings
    except ImportError:
        logger.warning("aiokafka not installed — audit consumer disabled")
        return

    bootstrap = settings.redpanda_bootstrap_servers
    if not bootstrap:
        logger.warning("REDPANDA_BOOTSTRAP_SERVERS not set — audit consumer disabled")
        return

    ssl_context = create_ssl_context()
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=bootstrap,
        group_id=GROUP_ID,
        security_protocol=settings.redpanda_security_protocol,
        sasl_mechanism=settings.redpanda_sasl_mechanism,
        sasl_plain_username=settings.redpanda_username,
        sasl_plain_password=settings.redpanda_password,
        ssl_context=ssl_context,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda m: m,
    )

    try:
        await consumer.start()
        logger.info("Audit consumer connected — listening on topic '%s'", TOPIC)
        async for msg in consumer:
            try:
                event = json.loads(msg.value.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.error("Audit consumer: malformed message, skipping — %s", exc)
                try:
                    await consumer.commit()
                except Exception:
                    pass
                continue

            last_exc = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    await record_event(event)
                    logger.debug(
                        "Audit recorded: event_type=%s task_id=%s (attempt %d)",
                        event.get("event_type"),
                        event.get("task_id"),
                        attempt,
                    )
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        "Audit consumer: persist attempt %d/%d failed — %s",
                        attempt, MAX_RETRIES, exc,
                    )
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(1)

            if last_exc is not None:
                logger.error(
                    "Audit consumer: dead-letter — failed after %d attempts for event_type=%s: %s",
                    MAX_RETRIES, event.get("event_type"), last_exc,
                )

            try:
                await consumer.commit()
            except Exception as commit_exc:
                logger.warning("Audit consumer: commit failed — %s", commit_exc)

    except asyncio.CancelledError:
        logger.info("Audit consumer shutting down")
        raise
    except Exception as exc:
        logger.error("Audit consumer: fatal error — %s", exc)
    finally:
        try:
            await consumer.stop()
        except Exception:
            pass
