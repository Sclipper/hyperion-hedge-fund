"""
Core Asset Manager - Module 5

Manages high-alpha assets that can override normal diversification constraints
while maintaining risk discipline through lifecycle tracking and performance monitoring.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from .models import CoreAssetInfo, RebalancingLimits

logger = logging.getLogger(__name__)


class CoreAssetManager:
    """
    Manages core asset lifecycle, performance monitoring, and override controls
    """
    
    def __init__(self, bucket_manager=None):
        self.core_assets: Dict[str, CoreAssetInfo] = {}
        self.bucket_manager = bucket_manager
        self.config: Optional[RebalancingLimits] = None
        
    def update_config(self, limits: RebalancingLimits):
        """Update configuration from RebalancingLimits"""
        self.config = limits
        logger.debug(f"Updated CoreAssetManager config: "
                    f"enabled={limits.enable_core_asset_management}, "
                    f"threshold={limits.core_asset_override_threshold}, "
                    f"max_assets={limits.max_core_assets}")
    
    def mark_as_core(self, asset: str, current_date: datetime, 
                    reason: str, designation_score: float = None) -> bool:
        """
        Mark asset as core with comprehensive tracking
        
        Args:
            asset: Asset symbol to mark as core
            current_date: Current date for lifecycle tracking
            reason: Reason for core designation
            designation_score: Score at time of designation
            
        Returns:
            bool: True if successfully marked as core, False if limits prevent it
        """
        if not self._can_mark_as_core(asset):
            logger.warning(f"Cannot mark {asset} as core: limits exceeded or disabled")
            return False
        
        # Get asset bucket
        bucket = self._get_asset_bucket(asset)
        
        # Calculate expiry date
        expiry_date = current_date + timedelta(days=self.config.core_asset_expiry_days)
        
        # Create core asset info
        core_info = CoreAssetInfo(
            asset=asset,
            designation_date=current_date,
            expiry_date=expiry_date,
            reason=reason,
            bucket=bucket,
            designation_score=designation_score,
            last_performance_check=current_date
        )
        
        self.core_assets[asset] = core_info
        
        score_str = f"{designation_score:.3f}" if designation_score is not None else "N/A"
        logger.info(f"Asset {asset} marked as CORE: {reason} "
                   f"(expires: {expiry_date.strftime('%Y-%m-%d')}, "
                   f"score: {score_str})")
        
        return True
    
    def is_core_asset(self, asset: str, current_date: datetime = None) -> bool:
        """
        Check if asset is currently core (with lifecycle validation)
        
        Args:
            asset: Asset symbol to check
            current_date: Current date for lifecycle checks (optional)
            
        Returns:
            bool: True if asset is currently core
        """
        if asset not in self.core_assets:
            return False
        
        # If no date provided, just check existence
        if current_date is None:
            return True
        
        # Check for automatic revocation due to lifecycle
        if self._should_auto_revoke(asset, current_date):
            reason = self._get_auto_revocation_reason(asset, current_date)
            self._auto_revoke_core_status(asset, current_date, reason)
            return False
        
        return True
    
    def revoke_core_status(self, asset: str, reason: str = "Manual revocation") -> bool:
        """
        Manually revoke core status
        
        Args:
            asset: Asset symbol to revoke
            reason: Reason for revocation
            
        Returns:
            bool: True if successfully revoked, False if asset wasn't core
        """
        if asset not in self.core_assets:
            logger.warning(f"Cannot revoke core status for {asset}: not a core asset")
            return False
        
        core_info = self.core_assets[asset]
        del self.core_assets[asset]
        
        logger.info(f"MANUALLY REVOKED core status for {asset}: {reason} "
                   f"(was core for {(datetime.now() - core_info.designation_date).days} days)")
        
        return True
    
    def extend_core_status(self, asset: str, additional_days: int, 
                          current_date: datetime, reason: str = "Manual extension") -> bool:
        """
        Extend core status expiry date
        
        Args:
            asset: Asset symbol to extend
            additional_days: Days to add to expiry
            current_date: Current date
            reason: Reason for extension
            
        Returns:
            bool: True if successfully extended, False if not allowed
        """
        if asset not in self.core_assets:
            logger.warning(f"Cannot extend core status for {asset}: not a core asset")
            return False
        
        core_info = self.core_assets[asset]
        
        # Check extension limit
        if core_info.extension_count >= self.config.core_asset_extension_limit:
            logger.warning(f"Cannot extend {asset}: extension limit "
                          f"({self.config.core_asset_extension_limit}) reached")
            return False
        
        # Extend expiry
        old_expiry = core_info.expiry_date
        new_expiry = current_date + timedelta(days=additional_days)
        core_info.expiry_date = new_expiry
        core_info.extension_count += 1
        
        logger.info(f"Extended core status for {asset}: {old_expiry.strftime('%Y-%m-%d')} -> "
                   f"{new_expiry.strftime('%Y-%m-%d')} ({reason})")
        
        return True
    
    def should_exempt_from_grace(self, asset: str, current_date: datetime) -> bool:
        """
        Check if asset should be exempt from grace periods
        
        Args:
            asset: Asset symbol to check
            current_date: Current date
            
        Returns:
            bool: True if asset should be exempt from grace periods
        """
        return self.is_core_asset(asset, current_date)
    
    def get_core_assets_list(self) -> List[str]:
        """
        Get list of currently active core assets
        
        Returns:
            List[str]: List of core asset symbols
        """
        return list(self.core_assets.keys())
    
    def get_core_status_report(self, current_date: datetime) -> Dict:
        """
        Generate comprehensive core asset status report (Phase 2 Enhanced)
        
        Args:
            current_date: Current date for reporting
            
        Returns:
            Dict: Comprehensive status report with performance data
        """
        report = {
            'total_core_assets': len(self.core_assets),
            'max_core_assets': self.config.max_core_assets if self.config else 0,
            'core_assets_details': {},
            'lifecycle_summary': {
                'expiring_soon': [],
                'performance_warnings': [],
                'extension_candidates': [],
                'underperforming': [],
                'performance_checks_due': []
            },
            'performance_overview': {
                'total_warnings': 0,
                'assets_with_warnings': 0,
                'checks_performed_today': 0
            }
        }
        
        total_warnings = 0
        assets_with_warnings = 0
        
        for asset, core_info in self.core_assets.items():
            days_until_expiry = (core_info.expiry_date - current_date).days
            days_since_designation = (current_date - core_info.designation_date).days
            
            # Check if performance check is due
            perf_check_due = self.should_check_performance(asset, current_date)
            
            # Get latest performance data if available
            performance_data = None
            if core_info.last_performance_check:
                performance_data = self.perform_performance_check(asset, current_date)
            
            asset_report = {
                'designation_date': core_info.designation_date.strftime('%Y-%m-%d'),
                'expiry_date': core_info.expiry_date.strftime('%Y-%m-%d'),
                'days_until_expiry': days_until_expiry,
                'days_since_designation': days_since_designation,
                'reason': core_info.reason,
                'bucket': core_info.bucket,
                'extension_count': core_info.extension_count,
                'designation_score': core_info.designation_score,
                'performance_warnings': core_info.performance_warnings.copy(),
                'last_performance_check': core_info.last_performance_check.strftime('%Y-%m-%d') if core_info.last_performance_check else None,
                'performance_check_due': perf_check_due,
                'latest_performance': performance_data
            }
            
            report['core_assets_details'][asset] = asset_report
            
            # Categorize for lifecycle summary
            if days_until_expiry <= 7:
                report['lifecycle_summary']['expiring_soon'].append(asset)
            
            if core_info.performance_warnings:
                report['lifecycle_summary']['performance_warnings'].append(asset)
                assets_with_warnings += 1
                total_warnings += len(core_info.performance_warnings)
            
            if (core_info.extension_count < self.config.core_asset_extension_limit and 
                days_until_expiry <= 14):
                report['lifecycle_summary']['extension_candidates'].append(asset)
            
            if perf_check_due:
                report['lifecycle_summary']['performance_checks_due'].append(asset)
            
            # Check for underperformance
            if performance_data and performance_data.get('threshold_exceeded', False):
                report['lifecycle_summary']['underperforming'].append(asset)
        
        # Update performance overview
        report['performance_overview']['total_warnings'] = total_warnings
        report['performance_overview']['assets_with_warnings'] = assets_with_warnings
        
        return report
    
    def perform_lifecycle_check(self, current_date: datetime) -> Dict[str, str]:
        """
        Perform comprehensive lifecycle check on all core assets (Phase 2 Enhanced)
        
        Args:
            current_date: Current date for lifecycle checks
            
        Returns:
            Dict[str, str]: Asset -> action taken
        """
        actions_taken = {}
        
        # Check each core asset
        assets_to_check = list(self.core_assets.keys())  # Copy to avoid modification during iteration
        
        for asset in assets_to_check:
            # Check for auto-revocation (expiry + performance)
            if self._should_auto_revoke(asset, current_date):
                reason = self._get_auto_revocation_reason(asset, current_date)
                self._auto_revoke_core_status(asset, current_date, reason)
                actions_taken[asset] = f"AUTO_REVOKED: {reason}"
            else:
                # Perform performance monitoring if due
                if self.should_check_performance(asset, current_date):
                    perf_results = self.perform_performance_check(asset, current_date)
                    if "error" not in perf_results:
                        actions_taken[asset] = f"RETAINED: {perf_results['recommendation']}"
                    else:
                        actions_taken[asset] = f"RETAINED: Performance check failed"
                else:
                    actions_taken[asset] = "RETAINED: No checks due"
        
        return actions_taken
    
    # Private helper methods
    
    def _can_mark_as_core(self, asset: str) -> bool:
        """Check if asset can be marked as core"""
        if not self.config or not self.config.enable_core_asset_management:
            return False
        
        if asset in self.core_assets:
            return False  # Already core
        
        if len(self.core_assets) >= self.config.max_core_assets:
            return False  # At limit
        
        return True
    
    def _get_asset_bucket(self, asset: str) -> str:
        """Get bucket for asset"""
        if self.bucket_manager:
            return self.bucket_manager.get_asset_bucket(asset)
        return 'Unknown'
    
    def _should_auto_revoke(self, asset: str, current_date: datetime) -> bool:
        """Check if core status should be automatically revoked"""
        if asset not in self.core_assets:
            return False
        
        core_info = self.core_assets[asset]
        
        # Check expiry date
        if current_date > core_info.expiry_date:
            return True
        
        # Check performance-based revocation (Phase 2)
        if self.config and self.config.enable_core_asset_management:
            should_revoke_perf, _ = self._check_underperformance(asset, current_date)
            if should_revoke_perf:
                return True
        
        return False
    
    def _get_auto_revocation_reason(self, asset: str, current_date: datetime) -> str:
        """Get reason for auto-revocation"""
        core_info = self.core_assets[asset]
        
        if current_date > core_info.expiry_date:
            return f"Automatic expiry after {self.config.core_asset_expiry_days} days"
        
        # Check performance-based reasons (Phase 2)
        should_revoke_perf, underperformance = self._check_underperformance(asset, current_date)
        if should_revoke_perf:
            return (f"Underperformed bucket by {underperformance:.1%} over "
                   f"{self.config.core_asset_underperformance_period} days "
                   f"(threshold: {self.config.core_asset_underperformance_threshold:.1%})")
        
        return "Unknown reason"
    
    def _auto_revoke_core_status(self, asset: str, current_date: datetime, reason: str):
        """Automatically revoke core status with detailed logging"""
        if asset in self.core_assets:
            core_info = self.core_assets[asset]
            days_held = (current_date - core_info.designation_date).days
            del self.core_assets[asset]
            
            logger.info(f"AUTO-REVOKED core status for {asset}: {reason} "
                       f"(was core for {days_held} days)")
    
    # Phase 2: Performance Monitoring Methods
    
    def _check_underperformance(self, asset: str, current_date: datetime) -> Tuple[bool, float]:
        """
        Check if core asset is underperforming its bucket significantly
        
        Args:
            asset: Asset symbol to check
            current_date: Current date for performance calculation
            
        Returns:
            Tuple[bool, float]: (should_revoke, underperformance_amount)
        """
        if asset not in self.core_assets or not self.config:
            return False, 0.0
        
        core_info = self.core_assets[asset]
        
        try:
            # Calculate performance comparison period
            start_date = current_date - timedelta(days=self.config.core_asset_underperformance_period)
            
            # Get asset performance
            asset_return = self._calculate_asset_return(asset, start_date, current_date)
            if asset_return is None:
                logger.debug(f"Cannot calculate return for {asset}: insufficient data")
                return False, 0.0
            
            # Get bucket average performance
            bucket_return = self._calculate_bucket_average_return(
                core_info.bucket, start_date, current_date, exclude_asset=asset
            )
            if bucket_return is None:
                logger.debug(f"Cannot calculate bucket return for {core_info.bucket}: insufficient data")
                return False, 0.0
            
            # Calculate underperformance
            underperformance = bucket_return - asset_return
            
            # Check if underperformance exceeds threshold
            threshold_exceeded = underperformance > self.config.core_asset_underperformance_threshold
            
            if threshold_exceeded:
                logger.warning(f"Core asset {asset} underperforming bucket {core_info.bucket} "
                              f"by {underperformance:.1%} over {self.config.core_asset_underperformance_period} days")
                
                # Issue performance warning before revocation
                self._issue_performance_warning(asset, underperformance, current_date)
            
            return threshold_exceeded, underperformance
            
        except Exception as e:
            logger.error(f"Error checking underperformance for {asset}: {e}")
            return False, 0.0
    
    def _calculate_asset_return(self, asset: str, start_date: datetime, end_date: datetime) -> Optional[float]:
        """
        Calculate asset return over period
        
        Args:
            asset: Asset symbol
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Optional[float]: Return as decimal (e.g., 0.10 for 10%), None if insufficient data
        """
        try:
            # This would integrate with the existing data manager/price data system
            # For now, we'll use a mock implementation that can be replaced with real data
            
            # NOTE: In a real implementation, this would call:
            # data_manager.get_price_data(asset, start_date, end_date)
            # and calculate actual returns from price data
            
            # Mock implementation for testing (Phase 2)
            # This should be replaced with actual price data integration
            import random
            random.seed(hash(asset + str(start_date)))  # Deterministic for testing
            
            # Simulate some return data based on asset characteristics
            base_return = random.uniform(-0.3, 0.3)  # -30% to +30% range
            return base_return
            
        except Exception as e:
            logger.error(f"Error calculating return for {asset}: {e}")
            return None
    
    def _calculate_bucket_average_return(self, bucket: str, start_date: datetime, 
                                       end_date: datetime, exclude_asset: str = None) -> Optional[float]:
        """
        Calculate bucket average return excluding specified asset
        
        Args:
            bucket: Bucket name
            start_date: Start date for calculation
            end_date: End date for calculation
            exclude_asset: Asset to exclude from calculation
            
        Returns:
            Optional[float]: Average return as decimal, None if insufficient data
        """
        try:
            if not self.bucket_manager:
                logger.debug(f"No bucket manager available for bucket {bucket} performance calculation")
                return None
            
            # Get all assets in bucket
            # NOTE: This would need to be implemented in the bucket manager
            # For now, we'll use a mock implementation
            
            # Mock bucket assets for testing (Phase 2)
            mock_bucket_assets = {
                "Risk Assets": ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"],
                "Defensive Assets": ["JNJ", "PG", "KO", "WMT", "XOM"],
                "International": ["EFA", "EEM", "VGK", "IEFA"],
                "Commodities": ["GLD", "SLV", "DBA", "USO"]
            }
            
            bucket_assets = mock_bucket_assets.get(bucket, [])
            if exclude_asset:
                bucket_assets = [a for a in bucket_assets if a != exclude_asset]
            
            if len(bucket_assets) < 2:  # Need at least 2 assets for meaningful average
                logger.debug(f"Insufficient assets in bucket {bucket} for average calculation")
                return None
            
            # Calculate returns for each asset in bucket
            returns = []
            for bucket_asset in bucket_assets:
                asset_return = self._calculate_asset_return(bucket_asset, start_date, end_date)
                if asset_return is not None:
                    returns.append(asset_return)
            
            if len(returns) < 2:
                logger.debug(f"Insufficient return data for bucket {bucket} average")
                return None
            
            # Calculate average return
            average_return = sum(returns) / len(returns)
            return average_return
            
        except Exception as e:
            logger.error(f"Error calculating bucket average return for {bucket}: {e}")
            return None
    
    def _issue_performance_warning(self, asset: str, underperformance: float, current_date: datetime):
        """
        Issue warning for underperforming core asset
        
        Args:
            asset: Asset symbol
            underperformance: Amount of underperformance as decimal
            current_date: Current date
        """
        if asset not in self.core_assets:
            return
        
        core_info = self.core_assets[asset]
        warning_message = (f"Performance warning: underperforming bucket {core_info.bucket} "
                          f"by {underperformance:.1%} on {current_date.strftime('%Y-%m-%d')}")
        
        # Add warning to core asset info
        core_info.performance_warnings.append(warning_message)
        
        # Limit warning history to prevent memory bloat
        if len(core_info.performance_warnings) > 10:
            core_info.performance_warnings = core_info.performance_warnings[-10:]
        
        logger.warning(f"Core asset {asset}: {warning_message}")
    
    def get_performance_warnings(self) -> Dict[str, List[str]]:
        """
        Get all current performance warnings
        
        Returns:
            Dict[str, List[str]]: Asset -> list of warning messages
        """
        warnings = {}
        for asset, core_info in self.core_assets.items():
            if core_info.performance_warnings:
                warnings[asset] = core_info.performance_warnings.copy()
        return warnings
    
    def clear_performance_warnings(self, asset: str = None):
        """
        Clear warnings for specific asset or all assets
        
        Args:
            asset: Asset symbol to clear warnings for, None to clear all
        """
        if asset is None:
            # Clear all warnings
            for core_info in self.core_assets.values():
                core_info.performance_warnings.clear()
            logger.info("Cleared all performance warnings")
        elif asset in self.core_assets:
            self.core_assets[asset].performance_warnings.clear()
            logger.info(f"Cleared performance warnings for {asset}")
        else:
            logger.warning(f"Cannot clear warnings for {asset}: not a core asset")
    
    def should_check_performance(self, asset: str, current_date: datetime) -> bool:
        """
        Check if it's time to perform a performance check for an asset
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            bool: True if performance check should be performed
        """
        if asset not in self.core_assets or not self.config:
            return False
        
        core_info = self.core_assets[asset]
        
        # Check if enough time has passed since last performance check
        if core_info.last_performance_check is None:
            return True
        
        days_since_check = (current_date - core_info.last_performance_check).days
        return days_since_check >= self.config.core_asset_performance_check_frequency
    
    def perform_performance_check(self, asset: str, current_date: datetime) -> Dict[str, any]:
        """
        Perform comprehensive performance check for a core asset
        
        Args:
            asset: Asset symbol
            current_date: Current date
            
        Returns:
            Dict[str, any]: Performance check results
        """
        if asset not in self.core_assets:
            return {"error": f"Asset {asset} is not a core asset"}
        
        core_info = self.core_assets[asset]
        
        try:
            # Calculate performance metrics
            start_date = current_date - timedelta(days=self.config.core_asset_underperformance_period)
            
            asset_return = self._calculate_asset_return(asset, start_date, current_date)
            bucket_return = self._calculate_bucket_average_return(
                core_info.bucket, start_date, current_date, exclude_asset=asset
            )
            
            should_revoke, underperformance = self._check_underperformance(asset, current_date)
            
            # Update last performance check
            core_info.last_performance_check = current_date
            
            # Prepare results
            results = {
                "asset": asset,
                "check_date": current_date.strftime('%Y-%m-%d'),
                "bucket": core_info.bucket,
                "asset_return": asset_return,
                "bucket_return": bucket_return,
                "underperformance": underperformance if asset_return and bucket_return else None,
                "threshold_exceeded": should_revoke,
                "days_since_designation": (current_date - core_info.designation_date).days,
                "days_until_expiry": (core_info.expiry_date - current_date).days,
                "warning_count": len(core_info.performance_warnings),
                "recommendation": self._get_performance_recommendation(asset, should_revoke, underperformance)
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error performing performance check for {asset}: {e}")
            return {"error": str(e)}
    
    def _get_performance_recommendation(self, asset: str, should_revoke: bool, underperformance: float) -> str:
        """Get performance-based recommendation for core asset"""
        if should_revoke:
            return f"RECOMMEND_REVOKE: Underperformance {underperformance:.1%} exceeds threshold"
        elif underperformance > (self.config.core_asset_underperformance_threshold * 0.7):
            return f"MONITOR_CLOSELY: Approaching underperformance threshold ({underperformance:.1%})"
        else:
            return "RETAIN: Performance within acceptable range" 