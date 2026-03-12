"""
Reminder consumer — subscribes to the 'task-reminders' Redpanda topic.

Processes reminder_triggered events idempotently. On each message:
  - Parses the event JSON
  - Logs the reminder intent (placeholder for future notification delivery)
  - Commits the offset after processing

Crash-safety guarantees:
  - Malformed messages are logged and skipped (offset committed to avoid loops)
  - Graceful shutdown on asyncio.CancelledError
  - Consumer loop never raises unhandled exceptions
"""
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

TOPIC = "task-reminders"
GROUP_ID = "reminder-consumer-group"


async def run_reminder_consumer() -> None:
    """
    Long-running background task that consumes from the 'task-reminders' topic.
    Exits cleanly when cancelled. Logs a warning if Redpanda is unreachable.
    """
    try:
        from aiokafka import AIOKafkaConsumer
        from aiokafka.helpers import create_ssl_context
        from src.config import settings
    except ImportError:
        logger.warning("aiokafka not installed — reminder consumer disabled")
        return

    bootstrap = settings.redpanda_bootstrap_servers
    if not bootstrap:
        logger.warning("REDPANDA_BOOTSTRAP_SERVERS not set — reminder consumer disabled")
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
        logger.info("Reminder consumer connected — listening on topic '%s'", TOPIC)
        async for msg in consumer:
            try:
                event = json.loads(msg.value.decode("utf-8"))
                task_id = event.get("task_id") or event.get("payload", {}).get("task_id")
                user_id = event.get("user_id")
                title = event.get("payload", {}).get("title") or event.get("title")
                reminder_at = event.get("payload", {}).get("reminder_at") or event.get("reminder_at")
                logger.info(
                    "Reminder triggered — task_id=%s user_id=%s title=%r due=%s",
                    task_id,
                    user_id,
                    title,
                    reminder_at,
                )
                # TODO: invoke actual notification delivery (email, push, etc.)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.error("Reminder consumer: malformed message, skipping — %s", exc)
            except Exception as exc:
                logger.error("Reminder consumer: error processing message — %s", exc)
            finally:
                try:
                    await consumer.commit()
                except Exception as commit_exc:
                    logger.warning("Reminder consumer: commit failed — %s", commit_exc)
    except asyncio.CancelledError:
        logger.info("Reminder consumer shutting down")
        raise
    except Exception as exc:
        logger.error("Reminder consumer: fatal error — %s", exc)
    finally:
        try:
            await consumer.stop()
        except Exception:
            pass
