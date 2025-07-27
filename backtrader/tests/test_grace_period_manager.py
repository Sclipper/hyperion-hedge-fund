"""
Unit tests for GracePeriodManager

Tests all grace period functionality including:
- Grace period start/end cycles
- Decay calculations with various rates  
- Score recovery scenarios
- Edge cases and error conditions
"""

import pytest
from datetime import datetime, timedelta
from backtrader.core.grace_period_manager import GracePeriodManager, GracePosition, GraceAction


class TestGracePeriodManager:
    """Test suite for GracePeriodManager functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.manager = GracePeriodManager(
            grace_period_days=5,
            decay_rate=0.8,
            min_decay_factor=0.1
        )
        self.base_date = datetime(2024, 1, 15, 10, 0, 0)
        
    def test_initialization(self):
        """Test manager initialization and validation"""
        # Valid initialization
        manager = GracePeriodManager(grace_period_days=3, decay_rate=0.9, min_decay_factor=0.05)
        assert manager.grace_period_days == 3
        assert manager.decay_rate == 0.9
        assert manager.min_decay_factor == 0.05
        assert len(manager.grace_positions) == 0
        
        # Invalid grace period days
        with pytest.raises(ValueError, match="grace_period_days must be 1-30"):
            GracePeriodManager(grace_period_days=0)
            
        with pytest.raises(ValueError, match="grace_period_days must be 1-30"):
            GracePeriodManager(grace_period_days=35)
            
        # Invalid decay rate
        with pytest.raises(ValueError, match="decay_rate must be 0.1-1.0"):
            GracePeriodManager(decay_rate=0.05)
            
        with pytest.raises(ValueError, match="decay_rate must be 0.1-1.0"):
            GracePeriodManager(decay_rate=1.5)
            
        # Invalid min decay factor
        with pytest.raises(ValueError, match="min_decay_factor must be 0.01-0.5"):
            GracePeriodManager(min_decay_factor=0.005)
            
        with pytest.raises(ValueError, match="min_decay_factor must be 0.01-0.5"):
            GracePeriodManager(min_decay_factor=0.8)
    
    def test_position_above_threshold_no_grace_period(self):
        """Test position with score above threshold (no grace period needed)"""
        action = self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.75,
            current_size=0.10,
            min_threshold=0.60,
            current_date=self.base_date
        )
        
        assert action.action == 'hold'
        assert action.new_size == 0.10
        assert 'above threshold' in action.reason
        assert not self.manager.is_in_grace_period('AAPL')
    
    def test_start_grace_period(self):
        """Test starting a new grace period for underperforming position"""
        action = self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.15,
            min_threshold=0.60,
            current_date=self.base_date
        )
        
        assert action.action == 'grace_start'
        assert action.new_size == 0.15  # No decay on first day
        assert action.days_in_grace == 0
        assert 'Starting grace period' in action.reason
        assert self.manager.is_in_grace_period('AAPL', self.base_date)
        
        # Verify grace position was created
        grace_status = self.manager.get_grace_status('AAPL', self.base_date)
        assert grace_status is not None
        assert grace_status['asset'] == 'AAPL'
        assert grace_status['original_size'] == 0.15
        assert grace_status['current_size'] == 0.15
        assert grace_status['days_in_grace'] == 0
        assert grace_status['days_remaining'] == 5
    
    def test_grace_period_decay_progression(self):
        """Test position decay over multiple days in grace period"""
        # Day 0: Start grace period
        action_day0 = self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.10,
            min_threshold=0.60,
            current_date=self.base_date
        )
        assert action_day0.action == 'grace_start'
        assert action_day0.new_size == 0.10
        
        # Day 1: First decay (0.10 * 0.8^1 = 0.08)
        day1 = self.base_date + timedelta(days=1)
        action_day1 = self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.10,
            min_threshold=0.60,
            current_date=day1
        )
        assert action_day1.action == 'grace_decay'
        assert action_day1.new_size == 0.08
        assert action_day1.days_in_grace == 1
        
        # Day 2: Second decay (0.10 * 0.8^2 = 0.064)
        day2 = self.base_date + timedelta(days=2)
        action_day2 = self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.08,
            min_threshold=0.60,
            current_date=day2
        )
        assert action_day2.action == 'grace_decay'
        assert action_day2.new_size == 0.064
        assert action_day2.days_in_grace == 2
        
        # Day 3: Third decay (0.10 * 0.8^3 = 0.0512)
        day3 = self.base_date + timedelta(days=3)
        action_day3 = self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.064,
            min_threshold=0.60,
            current_date=day3
        )
        assert action_day3.action == 'grace_decay'
        assert action_day3.new_size == 0.0512
        assert action_day3.days_in_grace == 3
    
    def test_grace_period_with_minimum_decay_floor(self):
        """Test that decay respects minimum decay factor floor"""
        # Start grace period
        self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.10,
            min_threshold=0.60,
            current_date=self.base_date
        )
        
        # Skip to day 10 (way past normal decay)
        # Normal decay: 0.10 * 0.8^10 = 0.00107... 
        # But min_decay_factor = 0.1, so floor is 0.10 * 0.1 = 0.01
        day10 = self.base_date + timedelta(days=10)
        action = self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.01,
            min_threshold=0.60,
            current_date=day10
        )
        
        # Should be force closed since day 10 > grace_period_days (5)
        assert action.action == 'force_close'
        assert action.new_size == 0.0
        assert action.force_close_triggered
    
    def test_grace_period_expiry_force_close(self):
        """Test force closure when grace period expires"""
        # Start grace period
        self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.10,
            min_threshold=0.60,
            current_date=self.base_date
        )
        
        # Grace period expires on day 5
        day5 = self.base_date + timedelta(days=5)
        action = self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,  # Still below threshold
            current_size=0.03277,  # Whatever decay led to
            min_threshold=0.60,
            current_date=day5
        )
        
        assert action.action == 'force_close'
        assert action.new_size == 0.0
        assert action.days_in_grace == 5
        assert action.force_close_triggered
        assert 'Grace period expired' in action.reason
        assert not self.manager.is_in_grace_period('AAPL', day5)
    
    def test_score_recovery_during_grace_period(self):
        """Test position recovery during grace period"""
        # Start grace period
        self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.10,
            min_threshold=0.60,
            current_date=self.base_date
        )
        
        # Day 2: Score recovers above threshold
        day2 = self.base_date + timedelta(days=2)
        action = self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.75,  # Above threshold now
            current_size=0.064,   # Current decayed size
            min_threshold=0.60,
            current_date=day2
        )
        
        assert action.action == 'grace_recovery'
        assert action.new_size == 0.064  # Keep current size, don't restore to original
        assert action.days_in_grace == 2
        assert action.recovery_detected
        assert 'Score recovered' in action.reason
        assert not self.manager.is_in_grace_period('AAPL', day2)
    
    def test_multiple_assets_grace_periods(self):
        """Test managing multiple assets in grace periods simultaneously"""
        # Start grace periods for multiple assets
        assets_data = [
            ('AAPL', 0.55, 0.10),
            ('MSFT', 0.45, 0.15),
            ('GOOGL', 0.50, 0.08)
        ]
        
        for asset, score, size in assets_data:
            action = self.manager.handle_underperforming_position(
                asset=asset,
                current_score=score,
                current_size=size,
                min_threshold=0.60,
                current_date=self.base_date
            )
            assert action.action == 'grace_start'
        
        # Verify all are in grace period
        assert self.manager.is_in_grace_period('AAPL', self.base_date)
        assert self.manager.is_in_grace_period('MSFT', self.base_date)
        assert self.manager.is_in_grace_period('GOOGL', self.base_date)
        
        # Day 1: Check decay for all
        day1 = self.base_date + timedelta(days=1)
        for asset, score, size in assets_data:
            action = self.manager.handle_underperforming_position(
                asset=asset,
                current_score=score,
                current_size=size * 0.8,  # Expected decay
                min_threshold=0.60,
                current_date=day1
            )
            assert action.action == 'grace_decay'
            assert action.days_in_grace == 1
        
        # GOOGL recovers on day 2
        day2 = self.base_date + timedelta(days=2)
        recovery_action = self.manager.handle_underperforming_position(
            asset='GOOGL',
            current_score=0.70,  # Recovered
            current_size=0.0512,  # Current size after 2 days decay
            min_threshold=0.60,
            current_date=day2
        )
        assert recovery_action.action == 'grace_recovery'
        assert not self.manager.is_in_grace_period('GOOGL', day2)
        
        # AAPL and MSFT still in grace period
        assert self.manager.is_in_grace_period('AAPL', day2)
        assert self.manager.is_in_grace_period('MSFT', day2)
    
    def test_apply_grace_decay_method(self):
        """Test the apply_grace_decay method"""
        # Asset not in grace period
        result = self.manager.apply_grace_decay('AAPL', self.base_date)
        assert result is None
        
        # Start grace period
        self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.10,
            min_threshold=0.60,
            current_date=self.base_date
        )
        
        # Apply decay after 3 days
        day3 = self.base_date + timedelta(days=3)
        decayed_size = self.manager.apply_grace_decay('AAPL', day3)
        expected_size = 0.10 * (0.8 ** 3)  # 0.0512
        assert abs(decayed_size - expected_size) < 0.0001
    
    def test_should_force_close_method(self):
        """Test the should_force_close method"""
        # Asset not in grace period
        assert not self.manager.should_force_close('AAPL', self.base_date)
        
        # Start grace period
        self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.10,
            min_threshold=0.60,
            current_date=self.base_date
        )
        
        # Day 3: Should not force close yet
        day3 = self.base_date + timedelta(days=3)
        assert not self.manager.should_force_close('AAPL', day3)
        
        # Day 5: Should force close (grace period expired)
        day5 = self.base_date + timedelta(days=5)
        assert self.manager.should_force_close('AAPL', day5)
    
    def test_get_all_grace_positions(self):
        """Test getting status of all grace positions"""
        # No positions initially
        all_positions = self.manager.get_all_grace_positions(self.base_date)
        assert len(all_positions) == 0
        
        # Add multiple grace positions
        assets = ['AAPL', 'MSFT', 'GOOGL']
        for i, asset in enumerate(assets):
            self.manager.handle_underperforming_position(
                asset=asset,
                current_score=0.55,
                current_size=0.10 + i * 0.02,  # Different sizes
                min_threshold=0.60,
                current_date=self.base_date
            )
        
        # Get all positions after 2 days
        day2 = self.base_date + timedelta(days=2)
        all_positions = self.manager.get_all_grace_positions(day2)
        
        assert len(all_positions) == 3
        for asset in assets:
            assert asset in all_positions
            assert all_positions[asset]['days_in_grace'] == 2
            assert all_positions[asset]['days_remaining'] == 3
            assert all_positions[asset]['in_grace_period'] is True
    
    def test_clean_expired_positions(self):
        """Test cleaning up expired grace positions"""
        # Add positions on different days
        self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.10,
            min_threshold=0.60,
            current_date=self.base_date
        )
        
        day2 = self.base_date + timedelta(days=2)
        self.manager.handle_underperforming_position(
            asset='MSFT',
            current_score=0.55,
            current_size=0.10,
            min_threshold=0.60,
            current_date=day2
        )
        
        # Day 6: AAPL should be expired, MSFT should not
        day6 = self.base_date + timedelta(days=6)
        expired_count = self.manager.clean_expired_positions(day6)
        
        assert expired_count == 1  # Only AAPL expired
        assert not self.manager.is_in_grace_period('AAPL', day6)
        assert self.manager.is_in_grace_period('MSFT', day6)
    
    def test_get_configuration_summary(self):
        """Test configuration summary"""
        summary = self.manager.get_configuration_summary()
        
        expected_keys = [
            'grace_period_days', 'decay_rate', 'min_decay_factor',
            'active_grace_positions', 'decay_formula', 'minimum_size_floor'
        ]
        
        for key in expected_keys:
            assert key in summary
        
        assert summary['grace_period_days'] == 5
        assert summary['decay_rate'] == 0.8
        assert summary['min_decay_factor'] == 0.1
        assert summary['active_grace_positions'] == 0
        assert '0.8' in summary['decay_formula']
        assert '10%' in summary['minimum_size_floor']
    
    def test_edge_case_zero_score(self):
        """Test handling of zero or negative scores"""
        action = self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.0,
            current_size=0.10,
            min_threshold=0.60,
            current_date=self.base_date
        )
        
        assert action.action == 'grace_start'
        assert action.new_size == 0.10
    
    def test_edge_case_very_small_position_size(self):
        """Test handling of very small position sizes"""
        action = self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.001,  # Very small position
            min_threshold=0.60,
            current_date=self.base_date
        )
        
        assert action.action == 'grace_start'
        assert action.new_size == 0.001
        
        # Test decay with very small position
        day3 = self.base_date + timedelta(days=3)
        decay_action = self.manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.001 * (0.8 ** 3),
            min_threshold=0.60,
            current_date=day3
        )
        
        assert decay_action.action == 'grace_decay'
        assert decay_action.new_size > 0  # Should respect minimum decay factor
    
    def test_different_decay_rates(self):
        """Test different decay rate configurations"""
        # Fast decay manager
        fast_manager = GracePeriodManager(
            grace_period_days=5,
            decay_rate=0.5,  # 50% per day
            min_decay_factor=0.1
        )
        
        fast_manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.10,
            min_threshold=0.60,
            current_date=self.base_date
        )
        
        # After 2 days: 0.10 * 0.5^2 = 0.025
        day2 = self.base_date + timedelta(days=2)
        action = fast_manager.handle_underperforming_position(
            asset='AAPL',
            current_score=0.55,
            current_size=0.025,
            min_threshold=0.60,
            current_date=day2
        )
        
        assert action.action == 'grace_decay'
        assert action.new_size == 0.025
        
        # Slow decay manager
        slow_manager = GracePeriodManager(
            grace_period_days=5,
            decay_rate=0.95,  # 5% per day
            min_decay_factor=0.1
        )
        
        slow_manager.handle_underperforming_position(
            asset='MSFT',
            current_score=0.55,
            current_size=0.10,
            min_threshold=0.60,
            current_date=self.base_date
        )
        
        # After 2 days: 0.10 * 0.95^2 = 0.09025
        action_slow = slow_manager.handle_underperforming_position(
            asset='MSFT',
            current_score=0.55,
            current_size=0.09025,
            min_threshold=0.60,
            current_date=day2
        )
        
        assert action_slow.action == 'grace_decay'
        assert action_slow.new_size == 0.09025


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"]) 