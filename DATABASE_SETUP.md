# Database Setup Guide

This guide will help you set up a unified PostgreSQL database that both Prisma and SQLAlchemy can use.

## Current Status

✅ **Prisma Schema Updated** - Now includes both financial models and hedge fund flow management tables  
✅ **SQLAlchemy Connection Updated** - Now configured for PostgreSQL  
✅ **Alembic Migration Setup** - Now configured for PostgreSQL  
🔧 **Manual Steps Required** - You need to complete the setup below

## Step 1: Add DATABASE_URL to .env file

Add this line to the top of your `.env` file:

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/hyperion_hedge_fund
```

Replace the connection details with your actual PostgreSQL setup:
- `postgres` - your PostgreSQL username
- `password` - your PostgreSQL password  
- `localhost:5432` - your PostgreSQL host and port
- `hyperion_hedge_fund` - your database name

## Step 2: Install Dependencies

```bash
# Install PostgreSQL driver for Python
poetry install

# If you need to install Prisma client (if not already done)
cd app/frontend && npm install @prisma/client
```

## Step 3: Create PostgreSQL Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create the database
CREATE DATABASE hyperion_hedge_fund;

# Exit psql
\q
```

## Step 4: Run Database Migrations

### Option A: Use Prisma (Recommended)
```bash
# Generate Prisma client
npx prisma generate

# Push schema to database (creates all tables)
npx prisma db push
```

### Option B: Use Alembic (Alternative)
```bash
# From the backend directory
cd app/backend

# Create new migration (if needed)
poetry run alembic revision --autogenerate -m "Initial migration"

# Run migrations
poetry run alembic upgrade head
```

## Step 5: Verify Setup

Both ORMs should now be able to connect to the same PostgreSQL database:

- **Prisma**: All your financial models (scheduler, kiss, dr_mo, position, etc.)
- **SQLAlchemy**: Hedge fund flow management (hedge_fund_flows, hedge_fund_flow_runs)

## Database Schema Structure

### Flow Management Tables (from SQLAlchemy):
- `hedge_fund_flows` - React Flow configurations
- `hedge_fund_flow_runs` - Execution tracking

### Financial Trading Tables (from Prisma):
- `scheduler` - Scheduled tasks
- `kiss` - Portfolio allocation (cash, stocks, gold, BTC)
- `dr_mo` - Market signals and positions
- `position` - Trading positions
- `research` - Research reports
- `scanner_assets` - Market scanning results

## Benefits of This Setup

✅ **Single Database** - Both ORMs connect to same PostgreSQL instance  
✅ **No Conflicts** - Each ORM manages its own tables  
✅ **Shared Access** - Both can read from any table when needed  
✅ **ACID Compliance** - PostgreSQL ensures data consistency  
✅ **Performance** - Better than SQLite for concurrent access

## Troubleshooting

If you encounter issues:

1. **Connection refused**: Ensure PostgreSQL is running
2. **Database doesn't exist**: Create it manually with `CREATE DATABASE hyperion_hedge_fund;`
3. **Permission denied**: Check PostgreSQL user permissions
4. **Port conflict**: Ensure port 5432 is available or update the DATABASE_URL 