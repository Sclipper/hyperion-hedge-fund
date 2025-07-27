from typing import Dict, List, Optional
from .base import DataProvider


class ProviderRegistry:
    """
    Manages data provider registration and selection
    """
    
    def __init__(self):
        self._providers: Dict[str, DataProvider] = {}
        self._active_provider: Optional[DataProvider] = None
        self._active_provider_name: Optional[str] = None
        
    def register(self, name: str, provider: DataProvider):
        """Register a new data provider"""
        self._providers[name] = provider
        
    def set_active(self, name: str):
        """Set the active data provider"""
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}. Available providers: {list(self._providers.keys())}")
        self._active_provider = self._providers[name]
        self._active_provider_name = name
        
    def get_active(self) -> DataProvider:
        """Get the currently active provider"""
        if not self._active_provider:
            raise RuntimeError("No active data provider set")
        return self._active_provider
    
    def get_active_name(self) -> str:
        """Get the name of the currently active provider"""
        if not self._active_provider_name:
            raise RuntimeError("No active data provider set")
        return self._active_provider_name
        
    def list_providers(self) -> List[str]:
        """List all registered provider names"""
        return list(self._providers.keys())
    
    def get_provider(self, name: str) -> DataProvider:
        """Get a specific provider by name"""
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}")
        return self._providers[name]