import time
import functools
import asyncio
from typing import Callable, Any
from pydantic import BaseModel
from datetime import datetime
from .logging import log_api_call, log_error


class Metric(BaseModel):
    name: str
    value: float
    timestamp: datetime
    tags: dict = {}


class MonitoringService:
    """
    Service for application monitoring and alerting
    """
    def __init__(self):
        self.metrics = []
        self.alerts = []

    def record_metric(self, name: str, value: float, tags: dict = None):
        """
        Record a metric
        """
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {}
        )
        self.metrics.append(metric)

    def time_function(self, metric_name: str = None):
        """
        Decorator to time function execution
        """
        def decorator(func: Callable) -> Callable:
            nonlocal metric_name
            if not metric_name:
                metric_name = f"{func.__module__}.{func.__name__}.execution_time"

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    self.record_metric(metric_name, execution_time)
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.record_metric(f"{metric_name}.error", execution_time)
                    raise e

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    self.record_metric(metric_name, execution_time)
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.record_metric(f"{metric_name}.error", execution_time)
                    raise e

            # Return the appropriate wrapper based on whether the function is async
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def check_alerts(self):
        """
        Check for conditions that trigger alerts
        """
        recent_metrics = [m for m in self.metrics if
                         (datetime.utcnow() - m.timestamp).seconds < 60]  # Last minute

        # Check for high error rates
        error_metrics = [m for m in recent_metrics if 'error' in m.name]
        if len(error_metrics) > 5:  # More than 5 errors in the last minute
            self.trigger_alert("High error rate detected", "error_rate_high",
                              {"error_count": len(error_metrics)})

        # Check for slow response times
        response_times = [m for m in recent_metrics if 'response_time' in m.name]
        if response_times:
            avg_response_time = sum(m.value for m in response_times) / len(response_times)
            if avg_response_time > 2.0:  # More than 2 seconds average
                self.trigger_alert("Slow response times detected", "slow_response",
                                  {"avg_response_time": avg_response_time})

    def trigger_alert(self, message: str, alert_type: str, details: dict = None):
        """
        Trigger an alert
        """
        alert = {
            "message": message,
            "type": alert_type,
            "timestamp": datetime.utcnow(),
            "details": details or {}
        }
        self.alerts.append(alert)

        # In a real implementation, this would send notifications to monitoring systems
        print(f"ALERT: {alert}")


# Global monitoring instance
monitoring_service = MonitoringService()


def monitor_api_call(endpoint: str):
    """
    Decorator to monitor API calls
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            user_id = kwargs.get('user_id') or (args[0] if args else None)

            try:
                result = await func(*args, **kwargs)
                response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

                # Log the API call
                log_api_call(endpoint, func.__name__, user_id, response_time)

                # Record the response time metric
                monitoring_service.record_metric(
                    f"api.response_time.{endpoint.replace('/', '_')}",
                    response_time,
                    {"endpoint": endpoint, "user_id": str(user_id) if user_id else "unknown"}
                )

                return result
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                log_error(e, f"API call failed: {endpoint}", user_id)
                monitoring_service.record_metric(
                    f"api.response_time.{endpoint.replace('/', '_')}.error",
                    response_time,
                    {"endpoint": endpoint, "user_id": str(user_id) if user_id else "unknown"}
                )
                raise e

        return wrapper

    return decorator