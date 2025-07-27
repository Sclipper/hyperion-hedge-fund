#!/usr/bin/env python3
"""
Database Connection Test Utility

Simple utility to test PostgreSQL database connectivity and validate
required tables for the hedge fund backtesting system.
"""

import sys
import os
from typing import Dict, Any

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from data.database_manager import get_database_manager, validate_database_config


def test_database_connection():
    """Test database connection and validate configuration"""
    print("=" * 60)
    print("Hedge Fund Backtrader - Database Connection Test")
    print("=" * 60)
    
    # Check configuration
    config = validate_database_config()
    
    print("\n1. Database Configuration:")
    print(f"   Has credentials: {config['has_credentials']}")
    print(f"   Can connect: {config['can_connect']}")
    
    if not config['has_credentials']:
        print("\n   Missing database credentials!")
        print("   Required environment variables:")
        for var in config['required_env_vars']:
            print(f"   - {var}")
        return False
    
    # Test connection
    db_manager = get_database_manager()
    
    print(f"\n2. Connection Details:")
    conn_info = db_manager.get_connection_info()
    print(f"   Connected: {conn_info['connected']}")
    print(f"   Has URL: {conn_info['has_url']}")
    
    if not conn_info['connected']:
        print("\n   ❌ Database connection failed!")
        return False
    
    print("   ✅ Database connection successful!")
    
    # Test required tables
    required_tables = ['research', 'scanner_historical']
    print(f"\n3. Required Tables Check:")
    
    all_tables_exist = True
    for table in required_tables:
        result = db_manager.execute_query(f"""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = '{table}'
        """)
        
        if result:
            print(f"   ✅ Table '{table}' exists")
        else:
            print(f"   ❌ Table '{table}' missing")
            all_tables_exist = False
    
    # Test data availability
    if all_tables_exist:
        print(f"\n4. Data Availability Check:")
        
        # Check research data
        research_count = db_manager.execute_query("""
            SELECT COUNT(*) as count FROM research 
            WHERE regime IS NOT NULL
        """)
        
        if research_count and research_count[0]['count'] > 0:
            print(f"   ✅ Research data: {research_count[0]['count']} records")
        else:
            print("   ⚠️  No regime research data found")
        
        # Check scanner data
        trending_count = db_manager.execute_query("""
            SELECT COUNT(*) as count FROM scanner_historical 
            WHERE market = 'trending'
        """)
        
        ranging_count = db_manager.execute_query("""
            SELECT COUNT(*) as count FROM scanner_historical 
            WHERE market = 'ranging'
        """)
        
        total_scanner_count = db_manager.execute_query("""
            SELECT COUNT(*) as count, 
                   COUNT(DISTINCT market) as market_types
            FROM scanner_historical
        """)
        
        if trending_count and trending_count[0]['count'] > 0:
            print(f"   ✅ Trending scanner data: {trending_count[0]['count']} records")
        else:
            print("   ⚠️  No trending scanner data found")
        
        if ranging_count and ranging_count[0]['count'] > 0:
            print(f"   ✅ Ranging scanner data: {ranging_count[0]['count']} records")
        else:
            print("   ⚠️  No ranging scanner data found")
        
        if total_scanner_count and total_scanner_count[0]['count'] > 0:
            total_records = total_scanner_count[0]['count']
            market_types = total_scanner_count[0]['market_types']
            print(f"   📊 Total scanner records: {total_records} across {market_types} market types")
    
    print(f"\n5. System Status:")
    if config['can_connect'] and all_tables_exist:
        print("   ✅ Database system fully operational")
        print("   ✅ Regime detection enabled")
        print("   ✅ Trending asset scanner enabled")
        return True
    else:
        print("   ⚠️  Database system partially operational")
        print("   ⚠️  System will use mock data where needed")
        return False


def show_environment_setup():
    """Show environment variable setup instructions"""
    print("\n" + "=" * 60)
    print("Environment Variable Setup Instructions")
    print("=" * 60)
    
    print("\nOption 1: Set DATABASE_URL (recommended)")
    print("export DATABASE_URL='postgresql://user:password@host:port/dbname'")
    
    print("\nOption 2: Set individual variables")
    print("export DB_HOST='localhost'")
    print("export DB_PORT='5432'")
    print("export DB_NAME='hedge_fund'")
    print("export DB_USER='postgres'")
    print("export DB_PASSWORD='your_password'")
    
    print("\nUsage Examples:")
    print("# Test connection")
    print("python utils/database_test.py")
    print("")
    print("# Run backtest with database")
    print("python main.py regime --buckets 'Risk Assets,Defensive Assets' --enable-database")
    print("")
    print("# Run without database (mock data)")
    print("python main.py regime --buckets 'Risk Assets,Defensive Assets' --enable-database=false")


if __name__ == '__main__':
    try:
        success = test_database_connection()
        
        if not success:
            show_environment_setup()
            sys.exit(1)
        else:
            print("\n✅ Database connection test completed successfully!")
            
    except Exception as e:
        print(f"\n❌ Database test failed with error: {e}")
        show_environment_setup()
        sys.exit(1)