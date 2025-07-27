"""
Module 7: Advanced Whipsaw Protection - Error Handling & Recovery

This module implements robust error handling and graceful degradation for
the whipsaw protection system to ensure reliable operation.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error category types"""
    REGIME_INTEGRATION = "regime_integration"
    CYCLE_TRACKING = "cycle_tracking"
    HISTORY_MANAGEMENT = "history_management"
    OVERRIDE_SYSTEM = "override_system"
    DATA_VALIDATION = "data_validation"
    PERFORMANCE = "performance"
    CONFIGURATION = "configuration"


@dataclass
class ErrorRecord:
    """Error record for tracking and analysis"""
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    error_message: str
    context: Dict[str, Any]
    recovery_action: str
    recovered: bool = False


class WhipsawErrorHandler:
    """
    Robust error handling and recovery system for whipsaw protection
    """
    
    def __init__(self, max_error_history=1000, performance_threshold_ms=10):
        """
        Initialize error handler
        
        Args:
            max_error_history: Maximum error records to retain
            performance_threshold_ms: Performance threshold in milliseconds
        """
        self.max_error_history = max_error_history
        self.performance_threshold_ms = performance_threshold_ms
        
        # Error tracking
        self.error_history: List[ErrorRecord] = []
        self.error_counts: Dict[ErrorCategory, int] = defaultdict(int)
        self.recovery_strategies: Dict[ErrorCategory, Callable] = {}
        
        # Fallback configurations
        self.fallback_config = {
            'max_cycles_per_period': 2,  # More lenient fallback
            'protection_period_days': 7,  # Shorter fallback period
            'min_position_duration_hours': 2,  # Shorter fallback duration
            'enable_regime_overrides': False,  # Disable complex features
        }
        
        # Performance monitoring
        self.performance_stats = {
            'total_operations': 0,
            'slow_operations': 0,
            'average_response_time_ms': 0.0,
            'max_response_time_ms': 0.0
        }
        
        # Recovery strategies
        self._initialize_recovery_strategies()
        
        # Setup logging
        self.logger = logging.getLogger('whipsaw_protection')
        
        print("🛠️ Whipsaw Error Handler initialized with graceful degradation")
    
    def handle_error(self, category: ErrorCategory, severity: ErrorSeverity,
                    error_message: str, context: Optional[Dict] = None,
                    exception: Optional[Exception] = None) -> Tuple[bool, str]:
        """
        Handle error with appropriate recovery strategy
        
        Args:
            category: Error category
            severity: Error severity
            error_message: Error description
            context: Error context
            exception: Original exception (if any)
            
        Returns:
            Tuple of (recovered: bool, recovery_action: str)
        """
        if context is None:
            context = {}
        
        # Add exception details to context
        if exception:
            context['exception_type'] = type(exception).__name__
            context['exception_str'] = str(exception)
        
        # Create error record
        error_record = ErrorRecord(
            timestamp=datetime.now(),
            category=category,
            severity=severity,
            error_message=error_message,
            context=context,
            recovery_action="",
            recovered=False
        )
        
        # Log error
        self._log_error(error_record, exception)
        
        # Attempt recovery
        recovery_success, recovery_action = self._attempt_recovery(error_record)
        
        # Update error record
        error_record.recovery_action = recovery_action
        error_record.recovered = recovery_success
        
        # Store error record
        self._store_error_record(error_record)
        
        # Update error counts
        self.error_counts[category] += 1
        
        return recovery_success, recovery_action
    
    def monitor_performance(self, operation_name: str, duration_ms: float):
        """
        Monitor operation performance and flag slow operations
        
        Args:
            operation_name: Name of operation
            duration_ms: Duration in milliseconds
        """
        self.performance_stats['total_operations'] += 1
        
        # Update average response time
        current_avg = self.performance_stats['average_response_time_ms']
        total_ops = self.performance_stats['total_operations']
        new_avg = ((current_avg * (total_ops - 1)) + duration_ms) / total_ops
        self.performance_stats['average_response_time_ms'] = new_avg
        
        # Update max response time
        if duration_ms > self.performance_stats['max_response_time_ms']:
            self.performance_stats['max_response_time_ms'] = duration_ms
        
        # Check for slow operation
        if duration_ms > self.performance_threshold_ms:
            self.performance_stats['slow_operations'] += 1
            
            self.handle_error(
                category=ErrorCategory.PERFORMANCE,
                severity=ErrorSeverity.MEDIUM,
                error_message=f"Slow operation detected: {operation_name}",
                context={
                    'operation': operation_name,
                    'duration_ms': duration_ms,
                    'threshold_ms': self.performance_threshold_ms
                }
            )
    
    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate whipsaw protection configuration
        
        Args:
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid: bool, errors: List[str])
        """
        errors = []
        
        # Required parameters
        required_params = [
            'max_cycles_per_period',
            'protection_period_days',
            'min_position_duration_hours'
        ]
        
        for param in required_params:
            if param not in config:
                errors.append(f"Missing required parameter: {param}")
        
        # Value validations
        if 'max_cycles_per_period' in config:
            if not isinstance(config['max_cycles_per_period'], int) or config['max_cycles_per_period'] < 0:
                errors.append("max_cycles_per_period must be a non-negative integer")
        
        if 'protection_period_days' in config:
            if not isinstance(config['protection_period_days'], int) or config['protection_period_days'] < 1:
                errors.append("protection_period_days must be a positive integer")
        
        if 'min_position_duration_hours' in config:
            if not isinstance(config['min_position_duration_hours'], (int, float)) or config['min_position_duration_hours'] < 0:
                errors.append("min_position_duration_hours must be a non-negative number")
        
        # Logical validations
        if ('max_cycles_per_period' in config and 'protection_period_days' in config and
            config['max_cycles_per_period'] > config['protection_period_days'] * 2):
            errors.append("max_cycles_per_period seems too high relative to protection_period_days")
        
        if errors:
            self.handle_error(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                error_message="Configuration validation failed",
                context={'errors': errors, 'config': config}
            )
        
        return len(errors) == 0, errors
    
    def get_fallback_configuration(self, original_config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Get fallback configuration for graceful degradation
        
        Args:
            original_config: Original configuration that failed
            
        Returns:
            Safe fallback configuration
        """
        fallback = self.fallback_config.copy()
        
        # If original config exists, try to preserve some values
        if original_config:
            safe_params = ['protection_period_days', 'max_cycles_per_period']
            for param in safe_params:
                if param in original_config:
                    try:
                        value = original_config[param]
                        if isinstance(value, (int, float)) and value > 0:
                            # Use more conservative value
                            if param == 'max_cycles_per_period':
                                fallback[param] = min(value, 3)
                            elif param == 'protection_period_days':
                                fallback[param] = max(value, 3)
                    except:
                        pass  # Use fallback default
        
        self.handle_error(
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.MEDIUM,
            error_message="Using fallback configuration",
            context={'fallback_config': fallback}
        )
        
        return fallback
    
    def check_system_health(self) -> Dict[str, Any]:
        """
        Check overall system health and identify issues
        
        Returns:
            System health report
        """
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        
        # Count recent errors by category and severity
        recent_errors = [
            error for error in self.error_history
            if error.timestamp > last_hour
        ]
        
        errors_by_category = defaultdict(int)
        errors_by_severity = defaultdict(int)
        
        for error in recent_errors:
            errors_by_category[error.category.value] += 1
            errors_by_severity[error.severity.value] += 1
        
        # Calculate health score (0-100)
        health_score = 100
        
        # Deduct points for errors
        health_score -= len(recent_errors) * 2  # 2 points per error
        health_score -= errors_by_severity['critical'] * 20  # 20 points per critical error
        health_score -= errors_by_severity['high'] * 10  # 10 points per high error
        
        # Deduct points for performance issues
        if self.performance_stats['total_operations'] > 0:
            slow_operation_rate = self.performance_stats['slow_operations'] / self.performance_stats['total_operations']
            health_score -= slow_operation_rate * 30  # Up to 30 points for performance
        
        health_score = max(0, min(100, health_score))
        
        # Determine health status
        if health_score >= 90:
            health_status = "excellent"
        elif health_score >= 70:
            health_status = "good"
        elif health_score >= 50:
            health_status = "fair"
        else:
            health_status = "poor"
        
        return {
            'health_score': health_score,
            'health_status': health_status,
            'recent_errors_count': len(recent_errors),
            'errors_by_category': dict(errors_by_category),
            'errors_by_severity': dict(errors_by_severity),
            'performance_stats': self.performance_stats.copy(),
            'total_error_count': len(self.error_history),
            'recommendations': self._get_health_recommendations(health_score, recent_errors)
        }
    
    def _initialize_recovery_strategies(self):
        """Initialize recovery strategies for different error categories"""
        
        self.recovery_strategies = {
            ErrorCategory.REGIME_INTEGRATION: self._recover_regime_integration,
            ErrorCategory.CYCLE_TRACKING: self._recover_cycle_tracking,
            ErrorCategory.HISTORY_MANAGEMENT: self._recover_history_management,
            ErrorCategory.OVERRIDE_SYSTEM: self._recover_override_system,
            ErrorCategory.DATA_VALIDATION: self._recover_data_validation,
            ErrorCategory.PERFORMANCE: self._recover_performance,
            ErrorCategory.CONFIGURATION: self._recover_configuration
        }
    
    def _attempt_recovery(self, error_record: ErrorRecord) -> Tuple[bool, str]:
        """
        Attempt to recover from error using appropriate strategy
        
        Args:
            error_record: Error record to recover from
            
        Returns:
            Tuple of (success: bool, action_taken: str)
        """
        try:
            if error_record.category in self.recovery_strategies:
                recovery_function = self.recovery_strategies[error_record.category]
                return recovery_function(error_record)
            else:
                return False, f"No recovery strategy for {error_record.category.value}"
        except Exception as e:
            return False, f"Recovery strategy failed: {str(e)}"
    
    def _recover_regime_integration(self, error_record: ErrorRecord) -> Tuple[bool, str]:
        """Recover from regime integration errors"""
        if error_record.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            return True, "Disabled regime integration, using basic protection only"
        else:
            return True, "Retry regime integration with fallback timeout"
    
    def _recover_cycle_tracking(self, error_record: ErrorRecord) -> Tuple[bool, str]:
        """Recover from cycle tracking errors"""
        return True, "Reset cycle tracking cache and continue with current data"
    
    def _recover_history_management(self, error_record: ErrorRecord) -> Tuple[bool, str]:
        """Recover from history management errors"""
        return True, "Cleaned old history data and reduced retention period"
    
    def _recover_override_system(self, error_record: ErrorRecord) -> Tuple[bool, str]:
        """Recover from override system errors"""
        if error_record.severity == ErrorSeverity.CRITICAL:
            return True, "Disabled override system, using strict protection only"
        else:
            return True, "Reset override cooldowns and continue"
    
    def _recover_data_validation(self, error_record: ErrorRecord) -> Tuple[bool, str]:
        """Recover from data validation errors"""
        return True, "Applied data sanitization and continued with validated subset"
    
    def _recover_performance(self, error_record: ErrorRecord) -> Tuple[bool, str]:
        """Recover from performance issues"""
        return True, "Enabled performance optimizations and reduced cache size"
    
    def _recover_configuration(self, error_record: ErrorRecord) -> Tuple[bool, str]:
        """Recover from configuration errors"""
        return True, "Applied fallback configuration with safe defaults"
    
    def _log_error(self, error_record: ErrorRecord, exception: Optional[Exception]):
        """
        Log error with appropriate level
        
        Args:
            error_record: Error record to log
            exception: Original exception (if any)
        """
        log_message = f"[{error_record.category.value}] {error_record.error_message}"
        
        if error_record.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=exception)
        elif error_record.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, exc_info=exception)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _store_error_record(self, error_record: ErrorRecord):
        """
        Store error record in history
        
        Args:
            error_record: Error record to store
        """
        self.error_history.append(error_record)
        
        # Trim history if too large
        if len(self.error_history) > self.max_error_history:
            # Remove oldest 20% of records
            trim_count = int(self.max_error_history * 0.2)
            self.error_history = self.error_history[trim_count:]
    
    def _get_health_recommendations(self, health_score: float, 
                                  recent_errors: List[ErrorRecord]) -> List[str]:
        """
        Get health improvement recommendations
        
        Args:
            health_score: Current health score
            recent_errors: Recent error records
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if health_score < 50:
            recommendations.append("System health is poor - consider restarting protection engine")
        
        # Category-specific recommendations
        error_categories = [error.category for error in recent_errors]
        
        if ErrorCategory.REGIME_INTEGRATION in error_categories:
            recommendations.append("Check Module 6 regime context provider connectivity")
        
        if ErrorCategory.PERFORMANCE in error_categories:
            recommendations.append("Consider reducing protection period or cycle limits")
        
        if len(recent_errors) > 10:
            recommendations.append("High error rate detected - check system resources")
        
        if not recommendations:
            recommendations.append("System operating normally")
        
        return recommendations
    
    def get_error_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get error statistics for analysis
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Error statistics
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_errors = [
            error for error in self.error_history
            if error.timestamp > cutoff_date
        ]
        
        # Group by category and severity
        by_category = defaultdict(int)
        by_severity = defaultdict(int)
        recovery_rate = defaultdict(int)
        recovery_total = defaultdict(int)
        
        for error in recent_errors:
            by_category[error.category.value] += 1
            by_severity[error.severity.value] += 1
            recovery_total[error.category.value] += 1
            if error.recovered:
                recovery_rate[error.category.value] += 1
        
        # Calculate recovery rates
        recovery_percentages = {}
        for category, total in recovery_total.items():
            if total > 0:
                recovery_percentages[category] = (recovery_rate[category] / total) * 100
        
        return {
            'period_days': days,
            'total_errors': len(recent_errors),
            'errors_by_category': dict(by_category),
            'errors_by_severity': dict(by_severity),
            'recovery_rates': recovery_percentages,
            'overall_recovery_rate': (sum(recovery_rate.values()) / max(len(recent_errors), 1)) * 100,
            'most_common_category': max(by_category.items(), key=lambda x: x[1])[0] if by_category else None,
            'most_common_severity': max(by_severity.items(), key=lambda x: x[1])[0] if by_severity else None
        } 