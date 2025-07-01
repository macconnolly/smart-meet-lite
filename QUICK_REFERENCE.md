# Smart-Meet Lite - Quick Reference

## 🚀 Starting the System

```bash
# Windows
setup_windows.bat    # First time setup
start_windows.bat    # Start the system

# Manual
docker-compose up -d # Start Qdrant
python -m src.api    # Start API
```

## 📍 URLs

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Qdrant Dashboard: http://localhost:6333/dashboard

## 🔑 Essential API Calls

### Ingest a Meeting

```python
import requests

# From transcript text
requests.post("http://localhost:8000/api/ingest", json={
    "title": "Team Meeting",
    "transcript": "Sarah: The login feature is complete..."
})

# From file
requests.post("http://localhost:8000/api/ingest/file",
    files={"file": open("meeting.txt", "rb")},
    data={"title": "Team Meeting"}
)
```

### Ask Business Intelligence Questions

```python
# Status questions
requests.post("http://localhost:8000/api/query", json={
    "query": "What's the status of the login feature?"
})

# Ownership questions
requests.post("http://localhost:8000/api/query", json={
    "query": "Who owns the payment system?"
})

# Timeline questions
requests.post("http://localhost:8000/api/query", json={
    "query": "How has the API performance changed over time?"
})

# Relationship questions
requests.post("http://localhost:8000/api/query", json={
    "query": "What depends on the billing system?"
})

# Analytics questions
requests.post("http://localhost:8000/api/query", json={
    "query": "How many features are in progress?"
})
```

### Search Memories

```python
# Basic search
requests.post("http://localhost:8000/api/search", json={
    "query": "authentication implementation",
    "limit": 5
})

# Search with entity filter
requests.post("http://localhost:8000/api/search", json={
    "query": "progress update",
    "entity_filter": ["Payment System", "Login Feature"]
})
```

### View Entities

```python
# List all entities
requests.get("http://localhost:8000/api/entities")

# Filter by type
requests.get("http://localhost:8000/api/entities?entity_type=project")

# Search entities
requests.get("http://localhost:8000/api/entities?search=payment")

# Get entity timeline
requests.get("http://localhost:8000/api/entities/{entity_id}/timeline")
```

### Analytics

```python
# Entity counts by type
requests.get("http://localhost:8000/api/analytics/entity_counts")

# State changes over time
requests.get("http://localhost:8000/api/analytics/state_changes")

# Relationship network
requests.get("http://localhost:8000/api/analytics/relationship_network")
```

## 🎯 Example Questions You Can Ask

### Project Status
- "What's the current status of [Project Name]?"
- "Which projects are blocked?"
- "Show me all projects in progress"

### Ownership & Responsibility
- "Who owns the [Feature Name]?"
- "What is [Person] working on?"
- "Who is responsible for [Task]?"

### Timeline & History
- "How has [Feature] progressed over time?"
- "When did [Project] status change?"
- "Show me the timeline for [Entity]"

### Relationships & Dependencies
- "What depends on [System]?"
- "Who works with [Person]?"
- "What blocks [Feature]?"

### Analytics & Metrics
- "How many features are we tracking?"
- "What's our project completion rate?"
- "Show me state changes this month"

## 🔧 Sample Transcript Format

```
Speaker Name: What they said goes here. Can be multiple sentences.

Another Person: Their response or comments.

Speaker Name: Follow-up discussion with specific details about features, deadlines, or assignments.
```

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Start the API: `python -m src.api` |
| "Qdrant error" | Start Docker: `docker-compose up -d` |
| "No entities found" | Check entity names match exactly |
| "Import error" | Activate venv: `venv\Scripts\activate` |
| "API key error" | Edit `.env` and add OpenRouter key |

## 📊 Entity Types

- **person**: Team members, stakeholders
- **project**: Projects, initiatives  
- **feature**: Features, components, modules
- **task**: Specific tasks, work items
- **decision**: Decisions made
- **deadline**: Dates, milestones
- **risk**: Risks, blockers, concerns
- **goal**: Objectives, targets
- **metric**: KPIs, measurements
- **team**: Teams, departments
- **system**: Systems, services
- **technology**: Tools, technologies

## 🔗 Relationship Types

- **owns**: Person owns project/feature/task
- **works_on**: Person works on something
- **reports_to**: Reporting structure
- **depends_on**: Dependencies
- **blocks**: Blocking relationships
- **assigned_to**: Assignments
- **responsible_for**: Responsibilities
