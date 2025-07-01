# Smart-Meet Lite v2.0

An intelligent meeting memory system with business intelligence capabilities.

## 🚀 Quick Start (Windows)

```bash
# 1. Run the setup script
setup_windows.bat

# 2. Start the system
start_windows.bat

# 3. Open in browser
http://localhost:8000
```

For detailed setup instructions, see **[SETUP_GUIDE.md](SETUP_GUIDE.md)**

## 🌟 Key Features

### Business Intelligence
- **Entity Tracking**: Automatically identifies and tracks people, projects, features, deadlines
- **State Management**: Monitors how entities change over time (planned → in_progress → completed)
- **Relationship Mapping**: Understands who owns what, dependencies, and assignments
- **Smart Queries**: Ask questions like "What's the status of Project X?" or "Who owns the payment feature?"
- **Timeline Tracking**: See how projects and features evolved across meetings
- **Analytics**: Get insights about your meeting data and organizational state

### Core Capabilities
- **Intelligent Extraction**: Uses LLM to extract structured information from meeting transcripts
- **Vector Search**: Find relevant discussions using semantic similarity
- **Dual Storage**: SQLite for metadata, Qdrant for vector embeddings
- **REST API**: Simple endpoints for ingestion and querying

## 📋 Prerequisites

- Python 3.11+
- Docker Desktop
- OpenRouter API key (get one at https://openrouter.ai/)

## 🎯 What Can It Do?

### Track Projects Through Their Lifecycle

```python
# Meeting 1: "We're starting the payment system project"
# Meeting 2: "Payment system is 40% complete"
# Meeting 3: "Payment system blocked by security review"
# Meeting 4: "Payment system launched successfully"

# Query: "Show me the payment system timeline"
# Answer: Complete history of status changes with reasons
```

### Answer Business Questions

```python
# Query: "Who owns the authentication feature?"
# Answer: "John owns Authentication Feature since last week"

# Query: "What's blocking our Q2 release?"
# Answer: "Security review for payment system (owned by Maria)"

# Query: "What are the current project statuses?"
# Answer: "3 projects in progress, 1 blocked, 2 completed"
```

## 📖 Documentation

- **[Setup Guide](SETUP_GUIDE.md)** - Detailed installation and configuration
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when running)
- **[Architecture Overview](#architecture)** - How it works under the hood

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Meeting   │────▶│  LLM Extract │────▶│   Process    │
│  Transcript │     │   Entities   │     │   & Store    │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                    ┌────────────────────────────┴────────┐
                    ▼                                     ▼
         ┌──────────────────┐                  ┌──────────────────┐
         │  Entity Storage  │                  │  Vector Storage  │
         │   (SQLite)       │                  │    (Qdrant)      │
         │  - Entities      │                  │  - Embeddings    │
         │  - States        │                  │  - Similarity    │
         │  - Relations     │                  └──────────────────┘
         │  - Transitions   │
         └──────────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │  Query Engine    │◀──── "What's the status of Project X?"
         │  - Parse Intent  │
         │  - Route Query   │────▶ "Project X is 75% complete,
         │  - Generate Answer│      owned by Sarah, on track for Q2"
         └──────────────────┘
```

## 🔧 Basic Usage

### 1. Ingest a Meeting

```python
import requests

response = requests.post("http://localhost:8000/api/ingest", json={
    "title": "Sprint Planning",
    "transcript": """
    Sarah: Let's review the authentication feature progress.
    John: I'm 60% done with OAuth implementation. 
    Sarah: Any blockers?
    John: Waiting on API keys from Google.
    Sarah: I'll handle that today.
    """
})
```

### 2. Ask Business Intelligence Questions

```python
# Status queries
response = requests.post("http://localhost:8000/api/query", json={
    "query": "What's the status of the authentication feature?"
})
# Answer: "Authentication Feature is currently in_progress with 60% progress, assigned to John."

# Ownership queries
response = requests.post("http://localhost:8000/api/query", json={
    "query": "Who is responsible for getting the API keys?"
})
# Answer: "Sarah is responsible for API keys."

# Timeline queries
response = requests.post("http://localhost:8000/api/query", json={
    "query": "How has the authentication feature progressed?"
})
# Answer: Shows timeline of all status changes
```

### 3. Search with Context

```python
# Search with entity filtering
response = requests.post("http://localhost:8000/api/search", json={
    "query": "implementation progress",
    "entity_filter": ["Authentication Feature"]
})
```

## 📊 API Endpoints

### Core Endpoints
- `POST /api/ingest` - Ingest meeting transcript
- `POST /api/ingest/file` - Upload transcript file
- `POST /api/query` - Ask business intelligence questions
- `POST /api/search` - Semantic search with filters

### Entity Endpoints
- `GET /api/entities` - List all tracked entities
- `GET /api/entities/{id}/timeline` - Entity history

### Analytics Endpoints
- `GET /api/analytics/entity_counts` - Entity statistics
- `GET /api/analytics/state_changes` - Change metrics

See full [API documentation](http://localhost:8000/docs) when running.

## 🧪 Testing

```bash
# Test system components
python test_bi_system.py

# Run simple examples
python example.py

# Run full business intelligence demo
python bi_demo.py
```

## 🐛 Troubleshooting

### Common Issues

1. **"Cannot connect to API"**
   - Ensure API is running: `python -m src.api`
   - Check port 8000 is free

2. **"Qdrant connection failed"**
   - Start Docker Desktop
   - Run: `docker-compose up -d`

3. **"OpenRouter API key not configured"**
   - Edit `.env` file
   - Add your key: `OPENROUTER_API_KEY=sk-or-...`

See [SETUP_GUIDE.md](SETUP_GUIDE.md#troubleshooting) for detailed troubleshooting.

## 📈 Example: Tracking a Project

The `bi_demo.py` script shows a complete example of tracking a mobile app redesign project:

1. **Kickoff**: Project starts, owners assigned, risks identified
2. **Week 2**: Progress updates, blockers emerge
3. **Month 1**: Mid-project status, solutions found
4. **Pre-release**: Final status, metrics exceeded

Then asks questions like:
- "What's the current status?"
- "Who owns what?"
- "How did performance improve?"
- "What were the risks?"

## 🔐 Production Considerations

This is a demonstration system. For production use:

- Add authentication/authorization
- Use PostgreSQL instead of SQLite
- Implement caching strategies
- Add monitoring and logging
- Set up backup procedures
- Rate limit API endpoints

## 📝 License

MIT

---

**Ready to get started?** Follow the **[Setup Guide](SETUP_GUIDE.md)** or run `setup_windows.bat` for automated setup on Windows.
