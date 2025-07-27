"""
PostgreSQL Database Manager for Hedge Fund Backtrader System

Provides connection management, configuration, and session handling for:
- Regime detection data
- Trending asset scanner results
- Macro research data
- Market sentiment analysis
"""

import os
import sys
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import logging


class DatabaseManager:
    """
    Centralized PostgreSQL database manager with connection pooling,
    error handling, and graceful degradation.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self.engine = None
        self.SessionLocal = None
        self.is_connected = False
        self._setup_logging()
        
        self.database_url = database_url or self._get_database_url_from_env()
        
        if self.database_url:
            self._initialize_connection()
    
    def _setup_logging(self):
        """Setup logging for database operations"""
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _get_database_url_from_env(self) -> Optional[str]:
        """
        Construct database URL from environment variables.
        
        Expected environment variables:
        - DATABASE_URL (full connection string)
        OR individual components:
        - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        """
        # Try full connection string first
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            return database_url
        
        # Try individual components
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        name = os.getenv('DB_NAME', 'hedge_fund')
        user = os.getenv('DB_USER', 'postgres')
        password = os.getenv('DB_PASSWORD')
        
        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{name}"
        else:
            self.logger.warning(
                "No database credentials found in environment variables. "
                "Database functionality will be disabled."
            )
            return None
    
    def _initialize_connection(self):
        """Initialize database connection and session factory"""
        try:
            self.engine = create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # Verify connections before use
                echo=False  # Set to True for SQL debugging
            )
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            self.is_connected = True
            self.logger.info("Database connection established successfully")
            
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
            self.is_connected = False
        except Exception as e:
            self.logger.error(f"Unexpected error during database initialization: {e}")
            self.is_connected = False
    
    def get_session(self) -> Optional[Session]:
        """
        Get a database session.
        
        Returns:
            Session object if connected, None otherwise
        """
        if not self.is_connected or not self.SessionLocal:
            return None
        
        try:
            return self.SessionLocal()
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to create database session: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test database connectivity.
        
        Returns:
            True if connection is working, False otherwise
        """
        if not self.is_connected:
            return False
        
        try:
            session = self.get_session()
            if session:
                session.execute(text("SELECT 1"))
                session.close()
                return True
        except SQLAlchemyError as e:
            self.logger.error(f"Database connection test failed: {e}")
        
        return False
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[list]:
        """
        Execute a query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result rows as dictionaries, None if error
        """
        if not self.is_connected:
            self.logger.warning("Database not connected - cannot execute query")
            return None
        
        session = self.get_session()
        if not session:
            return None
        
        try:
            result = session.execute(text(query), params or {})
            rows = [dict(row._mapping) for row in result]
            return rows
        except SQLAlchemyError as e:
            self.logger.error(f"Query execution failed: {e}")
            return None
        finally:
            session.close()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get database connection information.
        
        Returns:
            Dictionary with connection status and details
        """
        return {
            'connected': self.is_connected,
            'has_url': bool(self.database_url),
            'engine_info': str(self.engine.url) if self.engine else None,
            'pool_size': self.engine.pool.size() if self.engine and hasattr(self.engine.pool, 'size') else None
        }
    
    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            self.logger.info("Database connections closed")


# Global database manager instance
_db_manager = None


def get_database_manager() -> DatabaseManager:
    """
    Get the global database manager instance.
    
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_session() -> Optional[Session]:
    """
    Get a database session from the global manager.
    
    Returns:
        Session object if connected, None otherwise
    """
    return get_database_manager().get_session()


def test_database_connection() -> bool:
    """
    Test database connectivity using the global manager.
    
    Returns:
        True if connection is working, False otherwise
    """
    return get_database_manager().test_connection()


def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> Optional[list]:
    """
    Execute a query using the global manager.
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        List of result rows as dictionaries, None if error
    """
    return get_database_manager().execute_query(query, params)


# Database configuration validation
def validate_database_config() -> Dict[str, Any]:
    """
    Validate database configuration and return status.
    
    Returns:
        Dictionary with validation results
    """
    db_manager = get_database_manager()
    
    return {
        'has_credentials': bool(db_manager.database_url),
        'can_connect': db_manager.test_connection(),
        'connection_info': db_manager.get_connection_info(),
        'required_env_vars': [
            'DATABASE_URL or (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)'
        ]
    }