"""
Industrial-grade logging and monitoring system.
"""

import logging
import json
import time
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from contextvars import ContextVar
import structlog
from pythonjsonlogger import jsonlogger
import psutil
import requests
from src.services.local_cache import get_cache

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')

class StructuredLogger:
    """Industrial-grade structured logging."""
    
    def __init__(self):
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> structlog.BoundLogger:
        """Configure structured logging."""
        
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                self._add_context,
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        return structlog.get_logger()
    
    def _add_context(self, logger, method_name, event_dict):
        """Add request context to logs."""
        event_dict['request_id'] = request_id_var.get('')
        event_dict['user_id'] = user_id_var.get('')
        event_dict['service'] = 'vigilanteye-backend'
        event_dict['environment'] = 'production'  # Should be from config
        return event_dict
    
    def log_request(self, method: str, path: str, status_code: int, 
                   response_time: float, user_id: Optional[str] = None):
        """Log HTTP request."""
        self.logger.info(
            "HTTP Request",
            method=method,
            path=path,
            status_code=status_code,
            response_time_ms=response_time,
            user_id=user_id
        )
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log error with full context."""
        self.logger.error(
            "Application Error",
            error_type=type(error).__name__,
            error_message=str(error),
            traceback=traceback.format_exc(),
            context=context or {}
        )
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security events."""
        self.logger.warning(
            "Security Event",
            event_type=event_type,
            details=details,
            severity="high"
        )
    
    def log_business_event(self, event_type: str, details: Dict[str, Any]):
        """Log business events."""
        self.logger.info(
            "Business Event",
            event_type=event_type,
            details=details
        )

class PerformanceMonitor:
    """Monitor application performance metrics."""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
        self.cache = get_cache()
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a performance metric."""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            'value': value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'tags': tags or {}
        })
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'network_io': psutil.net_io_counters()._asdict(),
            'uptime': time.time() - self.start_time
        }
    
    def get_application_metrics(self) -> Dict[str, Any]:
        """Get application-specific metrics."""
        return {
            'total_requests': len(self.metrics.get('request_count', [])),
            'average_response_time': self._calculate_average('response_time'),
            'error_rate': self._calculate_error_rate(),
            'active_users': len(set(m.get('tags', {}).get('user_id', '') for m in self.metrics.get('user_activity', []))),
            'video_processing_queue': self.metrics.get('video_processing_queue', [0])[-1]
        }
    
    def _calculate_average(self, metric_name: str) -> float:
        """Calculate average for a metric."""
        values = [m['value'] for m in self.metrics.get(metric_name, [])]
        return sum(values) / len(values) if values else 0
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate."""
        total_requests = len(self.metrics.get('request_count', []))
        errors = len(self.metrics.get('error_count', []))
        return errors / total_requests if total_requests > 0 else 0

class AlertManager:
    """Manage alerts and notifications."""
    
    def __init__(self):
        self.alert_rules = {
            'high_error_rate': {'threshold': 0.05, 'window': 300},  # 5% in 5 minutes
            'high_cpu_usage': {'threshold': 80, 'window': 60},     # 80% for 1 minute
            'high_memory_usage': {'threshold': 85, 'window': 60},  # 85% for 1 minute
            'slow_response_time': {'threshold': 2000, 'window': 60}  # 2s for 1 minute
        }
        self.active_alerts = {}
    
    def check_alerts(self, metrics: Dict[str, Any]):
        """Check if any alerts should be triggered."""
        current_time = time.time()
        
        # Check error rate
        if metrics.get('error_rate', 0) > self.alert_rules['high_error_rate']['threshold']:
            self._trigger_alert('high_error_rate', metrics['error_rate'])
        
        # Check CPU usage
        if metrics.get('cpu_percent', 0) > self.alert_rules['high_cpu_usage']['threshold']:
            self._trigger_alert('high_cpu_usage', metrics['cpu_percent'])
        
        # Check memory usage
        if metrics.get('memory_percent', 0) > self.alert_rules['high_memory_usage']['threshold']:
            self._trigger_alert('high_memory_usage', metrics['memory_percent'])
        
        # Check response time
        if metrics.get('average_response_time', 0) > self.alert_rules['slow_response_time']['threshold']:
            self._trigger_alert('slow_response_time', metrics['average_response_time'])
    
    def _trigger_alert(self, alert_type: str, value: float):
        """Trigger an alert."""
        alert_key = f"{alert_type}_{int(time.time() // 60)}"  # Group by minute
        
        if alert_key not in self.active_alerts:
            self.active_alerts[alert_key] = {
                'type': alert_type,
                'value': value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'severity': 'high' if alert_type in ['high_error_rate', 'high_cpu_usage'] else 'medium'
            }
            
            # Send alert notification
            self._send_alert_notification(self.active_alerts[alert_key])
    
    def _send_alert_notification(self, alert: Dict[str, Any]):
        """Send alert notification (implement based on your notification system)."""
        # This could integrate with:
        # - Slack webhooks
        # - Email services
        # - PagerDuty
        # - Microsoft Teams
        # - Discord
        pass

class HealthChecker:
    """Comprehensive health checking system."""
    
    def __init__(self):
        self.checks = {
            'database': self._check_database,
            'redis': self._check_redis,
            'ai_services': self._check_ai_services,
            'storage': self._check_storage,
            'external_apis': self._check_external_apis
        }
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {}
        
        for check_name, check_func in self.checks.items():
            try:
                result = await check_func()
                results[check_name] = {
                    'status': 'healthy' if result else 'unhealthy',
                    'details': result
                }
            except Exception as e:
                results[check_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return results
    
    async def _check_database(self) -> bool:
        """Check database connectivity."""
        # Implement database health check
        return True
    
    async def _check_redis(self) -> bool:
        """Check Redis connectivity."""
        # Implement Redis health check
        return True
    
    async def _check_ai_services(self) -> bool:
        """Check AI services availability."""
        # Implement AI services health check
        return True
    
    async def _check_storage(self) -> bool:
        """Check storage availability."""
        # Implement storage health check
        return True
    
    async def _check_external_apis(self) -> bool:
        """Check external API dependencies."""
        # Implement external API health check
        return True

# Global instances
structured_logger = StructuredLogger()
performance_monitor = PerformanceMonitor()
alert_manager = AlertManager()
health_checker = HealthChecker()

# Convenience functions
def log_request(method: str, path: str, status_code: int, response_time: float, user_id: str = None):
    """Log HTTP request."""
    structured_logger.log_request(method, path, status_code, response_time, user_id)

def log_error(error: Exception, context: Dict[str, Any] = None):
    """Log error."""
    structured_logger.log_error(error, context)

def log_security_event(event_type: str, details: Dict[str, Any]):
    """Log security event."""
    structured_logger.log_security_event(event_type, details)

def log_business_event(event_type: str, details: Dict[str, Any]):
    """Log business event."""
    structured_logger.log_business_event(event_type, details)
