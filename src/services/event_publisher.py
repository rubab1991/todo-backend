"""
Dual-path event publisher for task events.

Publish strategy (in order):
  1. Dapr pub/sub HTTP sidecar — used when running under Kubernetes (Minikube).
  2. Direct aiokafka — fallback for Railway production where Dapr is unavailable.

MUST NEVER raise an unhandled exception. All failures are logged and swallowed.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# ── Dapr configuration ────────────────────────────────────────────────────────

DAPR_HTTP_PORT = int(os.getenv("DAPR_HTTP_PORT", "3500"))
DAPR_BASE_URL = f"http://localhost:{DAPR_HTTP_PORT}"
PUBSUB_NAME = "kafka-pubsub"

# ── Topic names ───────────────────────────────────────────────────────────────

TOPIC_TASK_EVENTS = "task-events"
TOPIC_TASK_REMINDERS = "task-reminders"
TOPIC_TASK_UPDATES = "task-updates"
TOPIC_AUDIT_EVENTS = "audit-events"

# ── aiokafka producer (module-level singleton) ────────────────────────────────

_kafka_producer = None


async def get_kafka_producer():
    """
    Return a cached AIOKafkaProducer, initialising it on first call.
    Returns None (and logs a warning) if configuration is missing or connection fails.
    Never raises.
    """
    global _kafka_producer
    if _kafka_producer is not None:
        return _kafka_producer

    try:
        from aiokafka import AIOKafkaProducer
        from aiokafka.helpers import create_ssl_context
        from src.config import settings

        bootstrap = settings.redpanda_bootstrap_servers
        username = settings.redpanda_username
        password = settings.redpanda_password
        sasl_mechanism = settings.redpanda_sasl_mechanism
        security_protocol = settings.redpanda_security_protocol

        if not bootstrap or not username or not password:
            logger.warning(
                "Redpanda env vars not configured — aiokafka producer disabled. "
                "Set REDPANDA_BOOTSTRAP_SERVERS, REDPANDA_USERNAME, REDPANDA_PASSWORD."
            )
            return None

        ssl_context = create_ssl_context()
        producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap,
            security_protocol=security_protocol,
            sasl_mechanism=sasl_mechanism,
            sasl_plain_username=username,
            sasl_plain_password=password,
            ssl_context=ssl_context,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await producer.start()
        _kafka_producer = producer
        logger.info("aiokafka producer connected to Redpanda (%s)", bootstrap)
        return _kafka_producer
    except ImportError:
        logger.warning("aiokafka not installed — direct Kafka publishing disabled")
        return None
    except Exception as exc:
        logger.warning("Failed to initialise aiokafka producer: %s", exc)
        return None


async def close_kafka_producer() -> None:
    """Stop the cached aiokafka producer. Call during application shutdown."""
    global _kafka_producer
    if _kafka_producer is not None:
        try:
            await _kafka_producer.stop()
            logger.info("aiokafka producer stopped")
        except Exception as exc:
            logger.warning("Error stopping aiokafka producer: %s", exc)
        finally:
            _kafka_producer = None


# ── Internal transport functions ──────────────────────────────────────────────

async def _publish_via_dapr(topic: str, event_data: Dict[str, Any]) -> bool:
    """Publish via Dapr sidecar HTTP API. Returns True on success, False otherwise."""
    url = f"{DAPR_BASE_URL}/v1.0/publish/{PUBSUB_NAME}/{topic}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                url,
                json=event_data,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code in (200, 204):
                logger.info(
                    "Dapr: published '%s' to topic '%s'",
                    event_data.get("event_type"),
                    topic,
                )
                return True
            logger.warning("Dapr publish returned %d for topic '%s'", resp.status_code, topic)
            return False
    except httpx.ConnectError:
        logger.debug("Dapr sidecar not reachable for topic '%s' — trying aiokafka", topic)
        return False
    except Exception as exc:
        logger.error("Dapr publish failed for topic '%s': %s", topic, exc)
        return False


async def _publish_via_kafka(topic: str, event_data: Dict[str, Any]) -> bool:
    """Publish directly via aiokafka. Returns True on success, False otherwise."""
    try:
        producer = await get_kafka_producer()
        if producer is None:
            return False
        await producer.send_and_wait(topic, value=event_data)
        logger.info(
            "aiokafka: published '%s' to topic '%s'",
            event_data.get("event_type"),
            topic,
        )
        return True
    except asyncio.TimeoutError:
        logger.error("aiokafka: timeout publishing to topic '%s'", topic)
        return False
    except Exception as exc:
        logger.error("aiokafka: failed to publish to topic '%s': %s", topic, exc)
        return False


# ── Public API ────────────────────────────────────────────────────────────────

async def publish_event(topic: str, event_data: Dict[str, Any]) -> bool:
    """
    Publish an event using the dual-path strategy.
    1. Try Dapr sidecar. If unavailable or fails, fall through.
    2. Try direct aiokafka (Railway production path).
    MUST NEVER raise.
    """
    try:
        if await _publish_via_dapr(topic, event_data):
            return True
        return await _publish_via_kafka(topic, event_data)
    except Exception as exc:
        logger.error("publish_event: unexpected error for topic '%s': %s", topic, exc)
        return False


async def publish_task_event(event_type: str, task_data: Dict[str, Any], user_id: str) -> bool:
    """Publish a task CRUD event to task-events and task-updates topics."""
    payload = {
        "event_type": event_type,
        "task_id": str(task_data.get("id", "")),
        "user_id": user_id,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "payload": task_data,
    }
    results = await asyncio.gather(
        publish_event(TOPIC_TASK_EVENTS, payload),
        publish_event(TOPIC_TASK_UPDATES, payload),
        return_exceptions=True,
    )
    return all(r is True for r in results)


async def publish_reminder_event(task_id: int, user_id: str, title: str, reminder_at: str) -> bool:
    """Publish a reminder scheduling event to the task-reminders topic."""
    payload = {
        "event_type": "reminder_triggered",
        "task_id": str(task_id),
        "user_id": user_id,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "payload": {
            "task_id": str(task_id),
            "title": title,
            "reminder_at": reminder_at,
        },
    }
    return await publish_event(TOPIC_TASK_REMINDERS, payload)


async def publish_audit_event(event_type: str, task_data: Dict[str, Any], user_id: str) -> bool:
    """Publish an audit event to the audit-events topic."""
    payload = {
        "event_type": event_type,
        "task_id": str(task_data.get("id", "")),
        "user_id": user_id,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "payload": task_data,
    }
    return await publish_event(TOPIC_AUDIT_EVENTS, payload)
