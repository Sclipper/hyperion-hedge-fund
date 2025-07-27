import logging
import time
import json
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import requests

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types"""
    RATE_LIMIT = "rate_limit"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    DATA_ERROR = "data_error"
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "auth_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorEvent:
    """Represents an error event"""
    timestamp: str
    error_type: ErrorType
    error_message: str
    ticker: str
    timeframe: str
    retry_count: int
    max_retries: int
    recovery_action: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ErrorRecoveryStrategy:
    """
    Advanced error handling and recovery strategies for Alpha Vantage API
    
    Features:
    - Intelligent retry with exponential backoff
    - Rate limit detection and handling
    - Circuit breaker pattern
    - Error classification and routing
    - Recovery action recommendations
    - Error event logging and analysis
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        
        # Circuit breaker state
        self.failure_count = 0
        self.last_failure_time = None
        self.circuit_open = False
        self.circuit_timeout = 300  # 5 minutes
        
        # Error tracking
        self.error_history = []
        self.rate_limit_backoff = 60  # 1 minute default
        
        # Error patterns for classification
        self.error_patterns = {
            ErrorType.RATE_LIMIT: [
                "call frequency",
                "rate limit",
                "too many requests",
                "API calls per minute exceeded"
            ],
            ErrorType.API_ERROR: [
                "Invalid API call",
                "Error Message",
                "the parameter",
                "function not found"
            ],
            ErrorType.AUTHENTICATION_ERROR: [
                "Invalid API key",
                "authentication failed",
                "unauthorized",
                "forbidden"
            ],
            ErrorType.QUOTA_EXCEEDED: [
                "monthly quota",
                "daily quota",
                "quota exceeded"
            ],
            ErrorType.NETWORK_ERROR: [
                "connection error",
                "timeout",
                "network unreachable",
                "dns resolution"
            ]
        }
        
        logger.info(f"ErrorRecoveryStrategy initialized with {max_retries} max retries")
    
    def classify_error(self, error: Exception, response_data: Dict = None) -> ErrorType:
        """
        Classify error type for appropriate handling
        
        Args:
            error: Exception that occurred
            response_data: API response data if available
            
        Returns:
            ErrorType classification
        """
        error_text = str(error).lower()
        
        # Check response data for API-specific errors
        if response_data:
            response_text = json.dumps(response_data).lower()
            error_text += " " + response_text
        
        # Check for specific error patterns
        for error_type, patterns in self.error_patterns.items():
            if any(pattern.lower() in error_text for pattern in patterns):
                return error_type
        
        # Check exception type
        if isinstance(error, requests.exceptions.ConnectionError):
            return ErrorType.NETWORK_ERROR
        elif isinstance(error, requests.exceptions.Timeout):
            return ErrorType.NETWORK_ERROR
        elif isinstance(error, requests.exceptions.HTTPError):
            if hasattr(error, 'response') and error.response:
                status_code = error.response.status_code
                if status_code == 429:
                    return ErrorType.RATE_LIMIT
                elif status_code in [401, 403]:
                    return ErrorType.AUTHENTICATION_ERROR
                else:
                    return ErrorType.API_ERROR
        
        return ErrorType.UNKNOWN_ERROR
    
    def should_retry(self, error_type: ErrorType, retry_count: int) -> bool:
        """
        Determine if operation should be retried
        
        Args:
            error_type: Classified error type
            retry_count: Current retry attempt
            
        Returns:
            True if should retry
        """
        # Check circuit breaker
        if self.circuit_open:
            if self.last_failure_time and \
               (datetime.now() - self.last_failure_time).seconds < self.circuit_timeout:
                logger.warning("Circuit breaker open - not retrying")
                return False
            else:
                # Reset circuit breaker
                self.circuit_open = False
                self.failure_count = 0
                logger.info("Circuit breaker reset")
        
        # Check retry count
        if retry_count >= self.max_retries:
            return False
        
        # Don't retry certain error types
        non_retryable = [
            ErrorType.AUTHENTICATION_ERROR,
            ErrorType.QUOTA_EXCEEDED,
            ErrorType.VALIDATION_ERROR
        ]
        
        if error_type in non_retryable:
            logger.warning(f"Error type {error_type} is not retryable")
            return False
        
        return True
    
    def get_retry_delay(self, error_type: ErrorType, retry_count: int) -> float:
        """
        Calculate retry delay based on error type and attempt
        
        Args:
            error_type: Classified error type
            retry_count: Current retry attempt
            
        Returns:
            Delay in seconds
        """
        if error_type == ErrorType.RATE_LIMIT:
            # For rate limits, use longer delays
            return self.rate_limit_backoff * (retry_count + 1)
        elif error_type == ErrorType.NETWORK_ERROR:
            # Exponential backoff for network errors
            return self.base_delay * (2 ** retry_count)
        else:
            # Standard exponential backoff
            return self.base_delay * (1.5 ** retry_count)
    
    def handle_error(self, error: Exception, ticker: str, timeframe: str,
                    retry_count: int, response_data: Dict = None) -> Dict[str, Any]:
        """
        Comprehensive error handling with recovery recommendations
        
        Args:
            error: Exception that occurred
            ticker: Symbol being processed
            timeframe: Data timeframe
            retry_count: Current retry count
            response_data: API response data
            
        Returns:
            Dict with recovery recommendations
        """
        error_type = self.classify_error(error, response_data)
        
        # Log error event
        error_event = ErrorEvent(
            timestamp=datetime.now().isoformat(),
            error_type=error_type,
            error_message=str(error),
            ticker=ticker,
            timeframe=timeframe,
            retry_count=retry_count,
            max_retries=self.max_retries,
            context={'response_data': response_data}
        )
        
        self.error_history.append(error_event)
        
        # Update circuit breaker
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= 5:  # Open circuit after 5 failures
            self.circuit_open = True
            logger.warning("Circuit breaker opened due to repeated failures")
        
        # Determine recovery strategy
        should_retry = self.should_retry(error_type, retry_count)
        retry_delay = self.get_retry_delay(error_type, retry_count) if should_retry else 0
        
        recovery_action = self._get_recovery_action(error_type, error_event)
        
        logger.error(f"Error handling {ticker} {timeframe}: {error_type.value} - {error}")
        
        if should_retry:
            logger.info(f"Will retry in {retry_delay:.1f} seconds (attempt {retry_count + 1}/{self.max_retries})")
        else:
            logger.error(f"Not retrying - {recovery_action}")
        
        return {
            'should_retry': should_retry,
            'retry_delay': retry_delay,
            'error_type': error_type,
            'error_event': error_event,
            'recovery_action': recovery_action,
            'circuit_open': self.circuit_open
        }
    
    def _get_recovery_action(self, error_type: ErrorType, error_event: ErrorEvent) -> str:
        """Get recommended recovery action for error type"""
        actions = {
            ErrorType.RATE_LIMIT: "Increase delay between requests or reduce request frequency",
            ErrorType.API_ERROR: "Check API parameters and ticker symbol validity",
            ErrorType.NETWORK_ERROR: "Check internet connection and API endpoint availability",
            ErrorType.DATA_ERROR: "Validate input parameters and data format",
            ErrorType.VALIDATION_ERROR: "Fix data validation issues",
            ErrorType.AUTHENTICATION_ERROR: "Check API key validity and permissions",
            ErrorType.QUOTA_EXCEEDED: "Wait for quota reset or upgrade API plan",
            ErrorType.UNKNOWN_ERROR: "Review error details and contact support if persistent"
        }
        
        return actions.get(error_type, "Manual intervention required")
    
    def execute_with_retry(self, operation: Callable, ticker: str, timeframe: str,
                          *args, **kwargs) -> Any:
        """
        Execute operation with intelligent retry logic
        
        Args:
            operation: Function to execute
            ticker: Symbol being processed
            timeframe: Data timeframe
            *args, **kwargs: Arguments for operation
            
        Returns:
            Operation result or raises final exception
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                # Check circuit breaker
                if self.circuit_open and retry_count > 0:
                    if self.last_failure_time and \
                       (datetime.now() - self.last_failure_time).seconds < self.circuit_timeout:
                        raise Exception("Circuit breaker open - operation blocked")
                
                # Execute operation
                result = operation(*args, **kwargs)
                
                # Success - reset failure count
                if retry_count > 0:
                    logger.info(f"Operation succeeded after {retry_count} retries")
                
                self.failure_count = max(0, self.failure_count - 1)
                return result
                
            except Exception as e:
                last_error = e
                
                # Handle error
                error_info = self.handle_error(e, ticker, timeframe, retry_count)
                
                if not error_info['should_retry']:
                    break
                
                # Wait before retry
                if error_info['retry_delay'] > 0:
                    time.sleep(error_info['retry_delay'])
                
                retry_count += 1
        
        # All retries exhausted
        logger.error(f"Operation failed after {retry_count} attempts for {ticker} {timeframe}")
        raise last_error
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and patterns"""
        if not self.error_history:
            return {'total_errors': 0}
        
        # Count errors by type
        error_counts = {}
        recent_errors = []
        
        # Look at last 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for event in self.error_history:
            event_time = datetime.fromisoformat(event.timestamp)
            
            # Count by type
            error_type = event.error_type.value
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            # Recent errors
            if event_time > cutoff_time:
                recent_errors.append(event)
        
        # Most common errors
        most_common = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'total_errors': len(self.error_history),
            'recent_errors_24h': len(recent_errors),
            'error_counts_by_type': error_counts,
            'most_common_errors': most_common[:5],
            'circuit_breaker_open': self.circuit_open,
            'failure_count': self.failure_count,
            'last_failure': self.last_failure_time.isoformat() if self.last_failure_time else None
        }
    
    def reset_circuit_breaker(self):
        """Manually reset circuit breaker"""
        self.circuit_open = False
        self.failure_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker manually reset")
    
    def adjust_rate_limit_backoff(self, new_backoff: float):
        """Adjust rate limit backoff period"""
        old_backoff = self.rate_limit_backoff
        self.rate_limit_backoff = new_backoff
        logger.info(f"Rate limit backoff adjusted from {old_backoff}s to {new_backoff}s")
    
    def export_error_log(self, filename: str = None) -> str:
        """Export error history to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_log_{timestamp}.json"
        
        error_data = [asdict(event) for event in self.error_history]
        
        with open(filename, 'w') as f:
            json.dump({
                'export_timestamp': datetime.now().isoformat(),
                'total_errors': len(error_data),
                'statistics': self.get_error_statistics(),
                'errors': error_data
            }, f, indent=2, default=str)
        
        logger.info(f"Error log exported to {filename}")
        return filename
    
    def clear_error_history(self, older_than_days: int = 7):
        """Clear old error history entries"""
        if not self.error_history:
            return 0
        
        cutoff_time = datetime.now() - timedelta(days=older_than_days)
        original_count = len(self.error_history)
        
        self.error_history = [
            event for event in self.error_history
            if datetime.fromisoformat(event.timestamp) > cutoff_time
        ]
        
        cleared_count = original_count - len(self.error_history)
        
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} error history entries older than {older_than_days} days")
        
        return cleared_count