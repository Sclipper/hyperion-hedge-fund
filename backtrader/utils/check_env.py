#!/usr/bin/env python3
"""
Environment Configuration Checker

Simple utility to verify .env file loading and database configuration.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

print("🔧 Environment Configuration Check")
print("=" * 50)

# Check if .env file exists
env_file = Path(__file__).parent.parent / '.env'
print(f"📁 .env file location: {env_file}")
print(f"📁 .env file exists: {env_file.exists()}")

if env_file.exists():
    print(f"📁 .env file size: {env_file.stat().st_size} bytes")

# Load dotenv and check environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(env_file)
    print("✅ python-dotenv loaded successfully")
except ImportError:
    print("❌ python-dotenv not installed")
    sys.exit(1)

print(f"\n🔗 Database Configuration:")
database_url = os.getenv('DATABASE_URL')
if database_url:
    # Mask password for security
    masked_url = database_url
    if '@' in masked_url and ':' in masked_url:
        parts = masked_url.split('@')
        if len(parts) == 2:
            auth_part = parts[0]
            if ':' in auth_part:
                user_pass = auth_part.split('://', 1)[1]
                if ':' in user_pass:
                    user, password = user_pass.split(':', 1)
                    masked_password = '*' * len(password)
                    masked_url = masked_url.replace(password, masked_password)
    
    print(f"✅ DATABASE_URL: {masked_url}")
else:
    print("❌ DATABASE_URL not found")

# Check individual components
db_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
print(f"\n🔧 Individual Database Variables:")
for var in db_vars:
    value = os.getenv(var)
    if value:
        if 'PASSWORD' in var:
            value = '*' * len(value)
        print(f"✅ {var}: {value}")
    else:
        print(f"⚪ {var}: Not set")

# Check additional environment variables
print(f"\n🎛️ Additional Configuration:")
additional_vars = [
    'ENABLE_ASSET_SCANNER_DATABASE',
    'ASSET_SCANNER_CONFIDENCE_THRESHOLD', 
    'ASSET_SCANNER_ENABLE_FALLBACK',
    'ASSET_SCANNER_CACHE_TTL',
    'REGIME_DETECTOR_USE_ENHANCED_SCANNER'
]

for var in additional_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {value}")
    else:
        print(f"⚪ {var}: Not set (using defaults)")

# Test database connection
print(f"\n🧪 Database Connection Test:")
try:
    from data.database_manager import get_database_manager
    
    db_manager = get_database_manager()
    if db_manager.is_connected:
        print("✅ Database connection successful")
        
        # Quick table check
        research_count = db_manager.execute_query("SELECT COUNT(*) as count FROM research")
        scanner_count = db_manager.execute_query("SELECT COUNT(*) as count FROM scanner_historical")
        
        if research_count:
            print(f"✅ Research table: {research_count[0]['count']} records")
        if scanner_count:
            print(f"✅ Scanner table: {scanner_count[0]['count']} records")
    else:
        print("❌ Database connection failed")
        
except Exception as e:
    print(f"❌ Database test error: {e}")

print(f"\n🎯 System Ready!")
print("You can now run:")
print("python main.py regime --buckets 'Risk Assets,Defensive Assets' --enable-database")