# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered hedge fund system with 17 different investment strategy agents (Warren Buffett, Charlie Munger, Cathie Wood, etc.) that collaborate to make trading decisions. The system supports both CLI and web interfaces and is designed for educational purposes only.

## Tech Stack

- **Backend**: Python 3.11+ with FastAPI, SQLAlchemy, and LangChain/LangGraph for multi-agent workflows
- **Frontend**: React 18 + TypeScript, Vite, Tailwind CSS, and @xyflow/react for visual workflow builder
- **Database**: SQLite (default) with PostgreSQL support via Alembic migrations
- **LLM Support**: OpenAI, Anthropic, Google, Groq, DeepSeek, and local Ollama models
- **Containerization**: Docker with compose setup

## Development Commands

### Python (Backend/CLI)
```bash
# Install dependencies
poetry install

# Run CLI hedge fund
poetry run python src/main.py --ticker AAPL,MSFT,NVDA

# Run backtester
poetry run python src/backtester.py --ticker AAPL,MSFT,NVDA

# Run tests
pytest

# Code formatting and linting
black src/ --line-length 420
isort src/
flake8 src/
```

### Frontend Development
```bash
cd app/frontend
npm install
npm run dev          # Development server on http://localhost:5173
npm run build        # Production build
npm run lint         # ESLint
```

### Full-Stack Web Application
```bash
cd app
./run.sh            # Mac/Linux - starts backend (port 8000) and frontend (port 5173)
run.bat             # Windows equivalent
```

### Docker
```bash
cd docker
./run.sh build                                    # Build image
./run.sh --ticker AAPL,MSFT,NVDA main           # Run hedge fund
./run.sh --ticker AAPL,MSFT,NVDA backtest       # Run backtester
```

## Architecture

### Multi-Agent System
- **17 Investment Strategy Agents**: Each implements a different investment philosophy
- **Risk Manager**: Calculates position limits and risk metrics  
- **Portfolio Manager**: Makes final trading decisions
- **LangGraph Orchestration**: Manages agent interactions and state flow

### Key Directories
- `src/agents/`: Individual agent implementations
- `src/tools/`: Financial data API integrations
- `src/graph/`: LangGraph state management
- `app/backend/`: FastAPI REST API with routes, services, repositories
- `app/frontend/src/`: React components, hooks, services, and types
- `app/frontend/src/nodes/`: React Flow node components for workflow builder

### Database Schema
- **HedgeFundFlow**: Stores React Flow configurations (nodes, edges, viewport)
- **HedgeFundFlowRun**: Tracks execution runs with status and results
- **Migrations**: Use `alembic upgrade head` after schema changes

## Configuration

### Environment Variables (.env)
- At least one LLM API key required: `OPENAI_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, or `DEEPSEEK_API_KEY`
- `FINANCIAL_DATASETS_API_KEY`: Required for tickers beyond AAPL, GOOGL, MSFT, NVDA, TSLA
- Database config for PostgreSQL support

### Code Style
- **Python**: Black formatting with 420 character line length, isort for imports
- **TypeScript**: ESLint with React rules, path aliases (@/*)
- **Important**: Follow existing patterns - check neighboring files for conventions

## Testing

- **Framework**: pytest for Python backend
- **Coverage**: Focus on API rate limiting and mock external dependencies
- **Run Command**: `pytest` from root directory

## Common CLI Options

- `--ticker AAPL,MSFT,NVDA`: Specify tickers to analyze
- `--start-date 2024-01-01 --end-date 2024-03-01`: Date range for analysis
- `--ollama`: Use local Ollama models instead of cloud LLMs  
- `--show-reasoning`: Print detailed agent reasoning to console

## Web Interface Features

- **Visual Workflow Builder**: Drag-and-drop agent configuration
- **Real-time Execution**: Live status updates during flow runs
- **Multi-tab Support**: Multiple flows in tabbed interface  
- **Theme Toggle**: Light/dark mode support
- **Settings Management**: API keys, model selection, appearance preferences