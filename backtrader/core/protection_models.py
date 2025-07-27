from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class ProtectionRequest:
    """
    Standardized protection request with complete context.
    """
    asset: str
    action: str  # 'open', 'close', 'increase', 'decrease'
    current_date: datetime
    current_size: Optional[float] = None
    target_size: Optional[float] = None
    current_score: Optional[float] = None
    target_score: Optional[float] = None
    reason: str = ""
    
    # Position context
    position_entry_date: Optional[datetime] = None
    position_entry_score: Optional[float] = None
    position_entry_size: Optional[float] = None
    
    # Portfolio context
    portfolio_allocation: Optional[float] = None
    active_positions: Optional[int] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """Validate request has required fields."""
        required_fields = ['asset', 'action', 'current_date']
        return all(getattr(self, field) is not None for field in required_fields)


@dataclass
class ProtectionResult:
    """Result from individual protection system check."""
    system_name: str
    blocks_action: bool
    reason: str
    priority: int
    check_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class ProtectionDecision:
    """
    Standardized protection decision with complete reasoning.
    """
    approved: bool
    reason: str
    blocking_systems: List[str] = field(default_factory=list)
    override_applied: bool = False
    override_reason: Optional[str] = None
    decision_hierarchy: List[ProtectionResult] = field(default_factory=list)
    decision_time_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary for logging."""
        return {
            'approved': self.approved,
            'reason': self.reason,
            'blocking_systems': self.blocking_systems,
            'override_applied': self.override_applied,
            'override_reason': self.override_reason,
            'decision_time_ms': self.decision_time_ms,
            'protection_checks': len(self.decision_hierarchy)
        }