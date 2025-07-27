"""
Module 9: Monitoring & Alerts - Portfolio Event Tracking System

This module provides comprehensive monitoring and audit capabilities for the
portfolio management system, capturing all decisions, regime changes, and
protection system activations in a unified event journal.
"""

from .event_store import EventStore
from .event_writer import EventWriter
from .event_models import (
    PortfolioEvent, 
    EventQuery, 
    EVENT_TYPES,
    EVENT_CATEGORIES
)

__version__ = "1.0.0"

__all__ = [
    'EventStore',
    'EventWriter', 
    'PortfolioEvent',
    'EventQuery',
    'EVENT_TYPES',
    'EVENT_CATEGORIES'
]
