"""Enhanced LLM-based memory extraction with business intelligence."""

import json
import re
import openai
import httpx
import warnings
from .models import Memory, ExtractionResult
from .config import settings

# Suppress SSL warnings in corporate environments
warnings.filterwarnings("ignore", message="Unverified HTTPS request")


class MemoryExtractor:
    """Extract structured memories and business intelligence from transcripts."""

    def __init__(self):
        """Initialize with OpenRouter client."""
        # Create HTTP client with SSL verification disabled for corporate networks
        http_client = httpx.Client(verify=False)

        self.client = openai.OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Smart-Meet Lite",
            },
            http_client=http_client,
        )

        self.system_prompt = """You are a business intelligence analyst extracting structured insights from meeting transcripts.

**CRITICAL INSTRUCTIONS:**
1.  **Use Full Entity Names:** When you identify an entity, extract its full, complete name. Do NOT truncate or shorten names. For example, if you see "the mobile app redesign project", the entity name is "mobile app redesign project", not "redesign project".
2.  **Be Consistent:** Use the exact same full entity name when defining relationships. If you extract an entity named "API optimization work", you must use "API optimization work" in the `from` or `to` field of any relationship involving it.

**EXAMPLE:**
- **Correct:** `{"name": "mobile app redesign project", "type": "project"}` and `{"from": "Mike", "to": "mobile app redesign project", "type": "works_on"}`
- **Incorrect:** `{"name": "redesign project", "type": "project"}` or `{"from": "Mike", "to": "the project", "type": "works_on"}`

Focus on extracting:
1. Key discussion points, decisions, and insights as memories
2. Business entities (people, projects, features, deadlines, metrics)
3. Relationships between entities (who owns what, dependencies, assignments)
4. State changes (status updates, progress changes)
5. Action items with assignees and deadlines
6. Key decisions made during the meeting

Entity Types:
- person: Team members, stakeholders
- project: High-level projects or initiatives
- feature: Specific features, modules, or components
- deadline: Dates, quarters, milestones
- metric: KPIs, measurements, targets
- team: Teams, departments
- system: Systems, services
- technology: Tools, technologies

Relationship Types:
- owns: Person owns project/feature/task
- works_on: Person works on something
- reports_to: Reporting structure
- depends_on: Dependencies
- blocks: Blocking relationships
- assigned_to: Assignments
- responsible_for: Responsibilities

For each entity, track its current state:
- Status (planned, in_progress, completed, blocked, etc.)
- Progress (percentage, milestones)
- Health (green, yellow, red)
- Priority (high, medium, low)
- Any other relevant state information

Return JSON with this exact structure:
{
  "memories": [{
    "content": "string",
    "speaker": "string or null",
    "timestamp": "string or null",
    "metadata": {"type": "decision|action|insight|discussion|risk|deadline", "importance": "high|medium|low", "tags": []},
    "entity_mentions": ["entity names mentioned"]
  }],
  "entities": [{
    "name": "string",
    "type": "person|project|feature|deadline|metric|team|system|technology",
    "current_state": {"status": "string", "progress": "string", "health": "string", "assigned_to": "string", "deadline": "string", "blockers": []},
    "attributes": {}
  }],
  "relationships": [{
    "from": "entity name",
    "to": "entity name",
    "type": "owns|works_on|reports_to|depends_on|blocks|assigned_to|responsible_for|collaborates_with",
    "attributes": {}
  }],
  "state_changes": [{
    "entity": "entity name",
    "from_state": {},
    "to_state": {},
    "reason": "string",
    "changed_fields": []
  }],
  "participants": ["names"],
  "topics": ["topics discussed"],
  "summary": "brief summary",
  "decisions": ["decision 1", "decision 2"],
  "action_items": [{"action": "string", "assignee": "name", "due": "date"}],
  "metadata": {
    "meeting_type": "string (e.g., client_meeting, internal_sync, executive_update, etc.)",
    "email_from": "sender email",
    "email_to": ["recipient emails"],
    "email_cc": ["cc emails"],
    "email_date": "email timestamp",
    "email_subject": "email subject line",
    "project_tags": ["related projects mentioned"],
    "actual_start_time": "meeting start time if mentioned",
    "actual_end_time": "meeting end time if mentioned",
    "organization_context": "organization/department context",
    "detailed_summary": "comprehensive 2-3 paragraph summary of the meeting",
    "key_metrics": {}
  }
}

When the input is an email, extract email headers (From, To, CC, Date, Subject) into the metadata fields.
Infer the meeting type from the content and participants.
Extract any project names or tags mentioned throughout the discussion.
Provide a detailed summary that captures the full context and outcomes."""

        # JSON Schema for structured output
        self.json_schema = {
            "name": "meeting_extraction",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "memories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "speaker": {"type": ["string", "null"]},
                                "timestamp": {"type": ["string", "null"]},
                                "metadata": {
                                    "type": "object",
                                    "properties": {
                                        "type": {
                                            "type": "string",
                                            "enum": [
                                                "decision",
                                                "action",
                                                "insight",
                                                "discussion",
                                                "risk",
                                                "deadline",
                                            ],
                                        },
                                        "importance": {
                                            "type": "string",
                                            "enum": ["high", "medium", "low"],
                                        },
                                        "tags": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                    "required": ["type", "importance"],
                                    "additionalProperties": False,
                                },
                                "entity_mentions": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["content", "metadata", "entity_mentions"],
                            "additionalProperties": False,
                        },
                    },
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {
                                    "type": "string",
                                    "enum": [
                                        "person",
                                        "project",
                                        "feature",
                                        "deadline",
                                        "metric",
                                        "team",
                                        "system",
                                        "technology",
                                    ],
                                },
                                "current_state": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "progress": {"type": ["string", "null"]},
                                        "health": {"type": ["string", "null"]},
                                        "assigned_to": {"type": ["string", "null"]},
                                        "deadline": {"type": ["string", "null"]},
                                        "blockers": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                    },
                                    "additionalProperties": True,
                                },
                                "attributes": {
                                    "type": "object",
                                    "additionalProperties": True,
                                },
                            },
                            "required": ["name", "type"],
                            "additionalProperties": False,
                        },
                    },
                    "relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from": {"type": "string"},
                                "to": {"type": "string"},
                                "type": {
                                    "type": "string",
                                    "enum": [
                                        "owns",
                                        "works_on",
                                        "reports_to",
                                        "depends_on",
                                        "blocks",
                                        "assigned_to",
                                        "responsible_for",
                                        "collaborates_with",
                                    ],
                                },
                                "attributes": {
                                    "type": "object",
                                    "additionalProperties": True,
                                },
                            },
                            "required": ["from", "to", "type"],
                            "additionalProperties": False,
                        },
                    },
                    "state_changes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "entity": {"type": "string"},
                                "from_state": {
                                    "type": "object",
                                    "additionalProperties": True,
                                },
                                "to_state": {
                                    "type": "object",
                                    "additionalProperties": True,
                                },
                                "reason": {"type": "string"},
                                "changed_fields": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["entity", "to_state"],
                            "additionalProperties": False,
                        },
                    },
                    "participants": {"type": "array", "items": {"type": "string"}},
                    "topics": {"type": "array", "items": {"type": "string"}},
                    "summary": {"type": "string"},
                    "decisions": {"type": "array", "items": {"type": "string"}},
                    "action_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string"},
                                "assignee": {"type": ["string", "null"]},
                                "due": {"type": ["string", "null"]},
                            },
                            "required": ["action"],
                            "additionalProperties": False,
                        },
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "meeting_type": {"type": "string"},
                            "key_metrics": {
                                "type": "object",
                                "additionalProperties": True,
                            },
                            "email_from": {"type": ["string", "null"]},
                            "email_to": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "email_cc": {
                                "type": "array", 
                                "items": {"type": "string"}
                            },
                            "email_date": {"type": ["string", "null"]},
                            "email_subject": {"type": ["string", "null"]},
                            "project_tags": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "actual_start_time": {"type": ["string", "null"]},
                            "actual_end_time": {"type": ["string", "null"]},
                            "organization_context": {"type": ["string", "null"]},
                            "detailed_summary": {"type": "string"},
                        },
                        "additionalProperties": True,
                    },
                },
                "required": [
                    "memories",
                    "entities",
                    "relationships",
                    "state_changes",
                    "participants",
                    "topics",
                    "summary",
                    "decisions",
                    "action_items",
                ],
                "additionalProperties": False,
            },
        }

    def extract(self, transcript: str, meeting_id: str) -> ExtractionResult:
        """Extract comprehensive business intelligence from transcript."""
        try:
            # Call OpenRouter API with structured output
            response = self.client.chat.completions.create(
                model=settings.clean_openrouter_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": f"Extract business intelligence from this transcript:\n\n{transcript}",
                    },
                ],
                temperature=0.3,
                max_tokens=20000,
                response_format={
                    "type": "json_schema",
                    "json_schema": self.json_schema,
                },
            )

            # Parse the structured response
            content = response.choices[0].message.content
            # print(f"\n=== LLM RESPONSE (first 2000 chars) ===\n{content[:2000]}\n===\n")  # Debug print

            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to decode LLM JSON response: {e}")
                print("--- Raw LLM Response ---")
                print(content)
                print("--- End Raw LLM Response ---")
                raise e

            # Process memories
            memories = []
            for mem_data in data.get("memories", []):
                memory = Memory(
                    meeting_id=meeting_id,
                    content=mem_data["content"],
                    speaker=mem_data.get("speaker"),
                    timestamp=mem_data.get("timestamp"),
                    metadata=mem_data.get("metadata", {}),
                    entity_mentions=mem_data.get("entity_mentions", []),
                )
                memories.append(memory)

            # Return comprehensive extraction
            return ExtractionResult(
                memories=memories,
                entities=data.get("entities", []),
                relationships=data.get("relationships", []),
                states=data.get("state_changes", []),
                meeting_metadata=data.get("metadata", {}),
                summary=data.get("summary", ""),
                topics=data.get("topics", []),
                participants=data.get("participants", []),
                decisions=data.get("decisions", []),
                action_items=data.get("action_items", []),
            )

        except Exception as e:
            print(f"LLM extraction failed: {e}. Using fallback method.")
            return self._fallback_extract(transcript, meeting_id)

    def _fallback_extract(self, transcript: str, meeting_id: str) -> ExtractionResult:
        """Enhanced fallback extraction with basic entity detection."""
        memories = []
        participants = set()
        entities = []
        decisions = []
        action_items = []

        # Try to find speaker patterns
        speaker_pattern = re.compile(r"^([A-Z][A-Za-z\s]+):\s*(.+)$", re.MULTILINE)
        matches = list(speaker_pattern.finditer(transcript))

        if matches:
            for match in matches:
                speaker = match.group(1).strip()
                content = match.group(2).strip()

                # Skip email headers
                if speaker.lower() in [
                    "to",
                    "from",
                    "subject",
                    "date",
                    "references",
                    "cc",
                    "bcc",
                ]:
                    continue

                participants.add(speaker)

                # Add person entity
                if not any(e["name"] == speaker for e in entities):
                    entities.append(
                        {
                            "name": speaker,
                            "type": "person",
                            "current_state": {"role": "participant"},
                            "attributes": {},
                        }
                    )

                # Detect decisions (simple heuristic)
                decision_keywords = [
                    "decided",
                    "will",
                    "going to",
                    "agreed",
                    "decision",
                ]
                for keyword in decision_keywords:
                    if keyword in content.lower():
                        decisions.append(content)
                        break

                # Detect action items
                action_keywords = ["will", "need to", "should", "must", "action"]
                if any(keyword in content.lower() for keyword in action_keywords):
                    action_items.append(
                        {"action": content, "assignee": speaker, "due": None}
                    )

                if (
                    settings.min_memory_length
                    <= len(content)
                    <= settings.max_memory_length
                ):
                    # Basic entity detection
                    entity_mentions = []

                    # Detect project/feature mentions
                    feature_keywords = [
                        "feature",
                        "module",
                        "component",
                        "service",
                        "system",
                        "project",
                    ]
                    for keyword in feature_keywords:
                        if keyword in content.lower():
                            # Extract potential entity name
                            words = content.split()
                            for i, word in enumerate(words):
                                if word.lower() == keyword and i > 0:
                                    entity_name = words[i - 1] + " " + word
                                    entity_mentions.append(entity_name)

                                    if not any(
                                        e["name"] == entity_name for e in entities
                                    ):
                                        entities.append(
                                            {
                                                "name": entity_name,
                                                "type": (
                                                    "feature"
                                                    if keyword != "project"
                                                    else "project"
                                                ),
                                                "current_state": {
                                                    "status": "discussed"
                                                },
                                                "attributes": {},
                                            }
                                        )

                    # Detect deadlines
                    deadline_patterns = [
                        r"\b(Q[1-4])\b",
                        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\b",
                    ]
                    for pattern in deadline_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            entity_mentions.append("deadline")

                    # Determine memory type
                    memory_type = "discussion"
                    if any(kw in content.lower() for kw in decision_keywords):
                        memory_type = "decision"
                    elif any(kw in content.lower() for kw in action_keywords):
                        memory_type = "action"

                    memory = Memory(
                        meeting_id=meeting_id,
                        content=content,
                        speaker=speaker,
                        metadata={"type": memory_type, "importance": "medium"},
                        entity_mentions=entity_mentions,
                    )
                    memories.append(memory)

        return ExtractionResult(
            memories=memories,
            entities=entities,
            relationships=[],
            states=[],
            meeting_metadata={},
            summary=f"Meeting with {len(participants)} participants discussing {len(set(e['name'] for e in entities if e['type'] in ['feature', 'project']))} features/projects",
            topics=list(
                set(e["name"] for e in entities if e["type"] in ["feature", "project"])
            ),
            participants=list(participants),
            decisions=decisions,  # Return all decisions
            action_items=action_items,  # Return all action items
        )
