# Smart-Meet Lite Setup Guide

This guide will walk you through setting up Smart-Meet Lite with business intelligence capabilities.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Setup](#quick-setup)
- [Detailed Setup](#detailed-setup)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [Testing the System](#testing-the-system)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- **Python 3.11+** (required)
- **Docker Desktop** (for Qdrant vector database)
- **OpenRouter API Key** (for LLM-based extraction)
- **Git** (to clone the repository)
- **8GB+ RAM** recommended

## Quick Setup

If you're comfortable with command line tools, here's the fastest way to get started:

```bash
# 1. Clone or navigate to the project
cd C:\Users\EL436GA\basic-memory\smart-meet-lite

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and configure environment
copy .env.example .env
# Edit .env and add your OpenRouter API key

# 5. Start Qdrant
docker-compose up -d

# 6. Download the AI model
python scripts/download_model.py

# 7. Initialize database
python scripts/setup.py

# 8. Start the API
python -m src.api

# 9. Test it works
python test_bi_system.py
```

The API will be available at http://localhost:8000

## Detailed Setup

### Step 1: Install Python 3.11+

1. Download Python from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Verify installation:
   ```bash
   python --version
   # Should show: Python 3.11.x or higher
   ```

### Step 2: Install Docker Desktop

1. Download Docker Desktop from https://www.docker.com/products/docker-desktop/
2. Install and start Docker Desktop
3. Verify installation:
   ```bash
   docker --version
   # Should show: Docker version xx.x.x
   ```

### Step 3: Get OpenRouter API Key

1. Go to https://openrouter.ai/
2. Sign up for an account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (starts with `sk-or-...`)

### Step 4: Set Up the Project

1. Open a terminal/command prompt
2. Navigate to the project directory:
   ```bash
   cd C:\Users\EL436GA\basic-memory\smart-meet-lite
   ```

3. Create a Python virtual environment:
   ```bash
   python -m venv venv
   ```

4. Activate the virtual environment:
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Mac/Linux
   source venv/bin/activate
   ```

5. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Step 5: Configure Environment

1. Copy the environment template:
   ```bash
   # Windows
   copy .env.example .env
   
   # Mac/Linux
   cp .env.example .env
   ```

2. Open `.env` in a text editor

3. Replace `your_openrouter_api_key_here` with your actual OpenRouter API key:
   ```
   OPENROUTER_API_KEY=sk-or-your-actual-key-here
   ```

4. Optionally, adjust other settings:
   ```
   # Change the LLM model (default is Claude 3 Haiku for speed/cost)
   OPENROUTER_MODEL=anthropic/claude-3-haiku
   
   # Or use GPT-4 for potentially better extraction
   OPENROUTER_MODEL=openai/gpt-4-turbo-preview
   ```

### Step 6: Start Qdrant Vector Database

1. Make sure Docker Desktop is running

2. Start Qdrant container:
   ```bash
   docker-compose up -d
   ```

3. Verify Qdrant is running:
   ```bash
   docker ps
   # Should show: smart-meet-lite-qdrant container running
   ```

4. Qdrant dashboard available at: http://localhost:6333/dashboard

### Step 7: Download the ONNX Model

The system uses a local AI model for generating embeddings:

```bash
python scripts/download_model.py
```

This downloads the `all-MiniLM-L6-v2` model (~90MB). If the download fails, you can manually download from:
https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/main/onnx

Save `model.onnx` to `models/onnx/all-MiniLM-L6-v2.onnx`

### Step 8: Initialize the Database

```bash
python scripts/setup.py
```

This will:
- Create the `data` directory
- Initialize SQLite database with all tables
- Create Qdrant collection
- Verify your configuration

You should see:
```
✓ Environment configured
✓ Initialized SQLite database
✓ Initialized Qdrant collection
✓ ONNX model found
✓ Setup complete!
```

### Step 9: Start the API Server

```bash
python -m src.api
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

The API is now running!

## Configuration

### Key Configuration Options (.env)

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_PATH=data/memories.db

# Qdrant Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=memories

# ONNX Model
ONNX_MODEL_PATH=models/onnx/all-MiniLM-L6-v2.onnx

# OpenRouter LLM Configuration
OPENROUTER_API_KEY=your_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=anthropic/claude-3-haiku

# Memory Extraction Settings
MIN_MEMORY_LENGTH=30    # Minimum characters for a memory
MAX_MEMORY_LENGTH=500   # Maximum characters for a memory
```

### Available LLM Models

You can change `OPENROUTER_MODEL` to use different models:

- `anthropic/claude-3-haiku` - Fast and cheap (default)
- `anthropic/claude-3-sonnet` - More capable
- `openai/gpt-4-turbo-preview` - Most capable
- `openai/gpt-3.5-turbo` - Good balance
- `google/gemini-pro` - Google's model

Check https://openrouter.ai/models for pricing and capabilities.

## Running the System

### Basic Usage

1. **Start all services:**
   ```bash
   # Terminal 1: Start Qdrant
   docker-compose up -d
   
   # Terminal 2: Start API
   python -m src.api
   ```

2. **Access the system:**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Qdrant Dashboard: http://localhost:6333/dashboard

3. **Run the demo:**
   ```bash
   # Simple examples
   python example.py
   
   # Full business intelligence demo
   python bi_demo.py
   ```

### Using the API

1. **Ingest a meeting:**
   ```python
   import requests
   
   response = requests.post("http://localhost:8000/api/ingest", json={
       "title": "Team Standup",
       "transcript": "John: I completed the login feature..."
   })
   ```

2. **Ask business intelligence questions:**
   ```python
   response = requests.post("http://localhost:8000/api/query", json={
       "query": "What is John working on?"
   })
   print(response.json()["answer"])
   ```

3. **Search memories:**
   ```python
   response = requests.post("http://localhost:8000/api/search", json={
       "query": "login feature",
       "limit": 5
   })
   ```

### Using the Makefile (Optional)

If you have `make` installed:

```bash
make setup       # Complete setup
make run         # Start the API
make test-api    # Test with sample data
make clean       # Clean cache files
```

## Testing the System

### 1. System Test

Run the comprehensive system test:

```bash
python test_bi_system.py
```

All tests should pass:
```
✓ Models imported
✓ Config imported
✓ Storage initialized
✓ All tests passed!
```

### 2. Simple Example

Test basic functionality:

```bash
python example.py
```

This will:
- Ingest a sample meeting
- Search for information
- Ask business questions
- Show tracked entities

### 3. Business Intelligence Demo

Run the full demo showing project lifecycle tracking:

```bash
python bi_demo.py
```

This demonstrates:
- Tracking a project across multiple meetings
- State changes over time
- Entity relationships
- Business intelligence queries

### 4. Manual Testing with Sample Data

Use the provided sample transcript:

```bash
curl -X POST http://localhost:8000/api/ingest/file \
  -F "file=@data/sample_transcript.txt" \
  -F "title=Architecture Review"
```

Then query:

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Who is leading the payment service?"}'
```

## Troubleshooting

### Common Issues

#### 1. "Cannot connect to API"
- Make sure the API is running: `python -m src.api`
- Check the port isn't in use: `netstat -an | findstr 8000`

#### 2. "Qdrant connection failed"
- Ensure Docker Desktop is running
- Start Qdrant: `docker-compose up -d`
- Check container: `docker ps`

#### 3. "OpenRouter API key not configured"
- Check `.env` file exists
- Verify key is set correctly (no quotes needed)
- Key should start with `sk-or-`

#### 4. "ONNX model not found"
- Run: `python scripts/download_model.py`
- Check `models/onnx/` directory
- Manually download if needed

#### 5. "Import errors"
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (needs 3.11+)

### Checking Service Status

```bash
# Check API is running
curl http://localhost:8000

# Check Qdrant is running
curl http://localhost:6333

# Check database exists
dir data\memories.db  # Windows
ls -la data/memories.db  # Mac/Linux
```

### Viewing Logs

The API shows logs in the terminal. For more detail:

```python
# In .env, set:
LOG_LEVEL=DEBUG
```

### Resetting the System

To start fresh:

```bash
# Stop services
docker-compose down

# Delete data
rm -rf data/memories.db
rm -rf data/qdrant/

# Recreate
python scripts/setup.py
```

## Next Steps

Once the system is running:

1. **Ingest your meetings** using the `/api/ingest` endpoint
2. **Ask questions** about your data using `/api/query`
3. **Explore entities** at `/api/entities`
4. **View analytics** at `/api/analytics/entity_counts`
5. **Check the API docs** at http://localhost:8000/docs

For production use:
- Set up proper authentication
- Use PostgreSQL instead of SQLite
- Deploy with proper monitoring
- Configure backup strategies

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Ensure all prerequisites are installed
3. Try the system test: `python test_bi_system.py`
4. Check for error messages in the API logs

The system is designed to be self-contained and should work out of the box once properly configured.
