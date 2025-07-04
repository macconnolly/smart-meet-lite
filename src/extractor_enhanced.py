"""Enhanced LLM-based extraction with comprehensive management consultant schema."""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import openai
import httpx
from .models import (
    Memory,
    Entity,
    EntityType,
    ExtractionResult,
)
from .config import settings

logger = logging.getLogger(__name__)


class EnhancedMeetingExtractor:
    """Extract comprehensive business intelligence from meeting transcripts."""

    def __init__(self, llm_client: openai.OpenAI):
        """Initialize with shared LLM client."""
        self.client = llm_client
        
        self.system_prompt = """You are a world-class management consultant and an expert notetaker. Your task is to analyze the provided meeting transcript and produce a highly detailed, structured set of internal notes.

Extract all available information according to the schema, but don't force fields that aren't applicable. Focus on:

1. **Strategic Context**: Decisions, risks, dependencies, cross-project impacts
2. **Deliverable Intelligence**: Requirements evolution, format preferences, stakeholder needs  
3. **Stakeholder Intelligence**: Communication preferences, concerns, interests
4. **Knowledge Connections**: Entity relationships and how they connect
5. **Implementation Insights**: Challenges, success criteria, dependencies

Remember:
- Use FULL entity names (e.g., "mobile app redesign project" not just "redesign")
- Capture requirement evolution when discussed
- Note stakeholder preferences and concerns
- Track decision rationale and impacts
- Identify risks with severity levels
- Connect entities with clear relationships

Even if you can only extract 50% of the schema fields, capture what's there. The goal is building organizational knowledge over time.

IMPORTANT: You must respond ONLY with valid JSON that matches the provided schema. Do not include any explanatory text before or after the JSON. Start your response with { and end with }."""

        # Your comprehensive JSON schema
        self.json_schema = {
            "name": "meeting_notes",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    # Core meeting metadata
                    "meeting_title": {"type": "string"},
                    "meeting_date": {"type": "string"},
                    "participants": {"type": "array", "items": {"type": "string"}},
                    "meeting_id": {"type": "string", "description": "Unique identifier for the meeting (e.g., project-YYYYMMDD-type)"},
                    "meeting_type": {"type": "string", "enum": ["project_standup", "status_update", "decision_making", "requirements_gathering", "stakeholder_alignment", "planning", "review", "other"]},
                    "meeting_duration": {"type": "integer", "description": "Duration in minutes"},
                    
                    # Summary fields
                    "executive_summary": {"type": "string"},
                    "executive_summary_bullets": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5},
                    
                    # Detailed minutes with enhanced structure
                    "detailed_minutes": {
                        "type": "object",
                        "properties": {
                            "sections": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "key_points": {"type": "array", "items": {"type": "string"}},
                                        "stakeholders_mentioned": {"type": "array", "items": {"type": "string"}},
                                        "deliverables_discussed": {"type": "array", "items": {"type": "string"}},
                                        "requirements_evolution": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "requirement": {"type": "string"},
                                                    "previous_state": {"type": "string"},
                                                    "current_state": {"type": "string"},
                                                    "stakeholder_source": {"type": "string"}
                                                }
                                            }
                                        }
                                    },
                                    "required": ["title", "key_points"]
                                }
                            }
                        },
                        "required": ["sections"]
                    },
                    
                    # Decision tracking with context
                    "key_decisions": {"type": "array", "items": {"type": "string"}},
                    "decisions_with_context": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "decision": {"type": "string"},
                                "rationale": {"type": "string"},
                                "stakeholders_involved": {"type": "array", "items": {"type": "string"}},
                                "impact_areas": {"type": "array", "items": {"type": "string"}},
                                "supersedes_decision": {"type": ["string", "null"]},
                                "decision_status": {"type": "string", "enum": ["proposed", "approved", "rejected", "pending", "implemented"]}
                            },
                            "required": ["decision", "rationale"]
                        }
                    },
                    
                    # Action items with enhanced tracking
                    "action_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "owner": {"type": "string"},
                                "due_date": {"type": ["string", "null"]},
                                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                                "tags": {"type": "array", "items": {"type": "string"}},
                                "suggested_next_steps": {"type": "string"},
                                "related_deliverable": {"type": ["string", "null"]},
                                "related_project": {"type": ["string", "null"]},
                                "status": {"type": "string", "enum": ["not_started", "in_progress", "blocked", "completed", "deferred"]},
                                "blockers": {"type": ["string", "null"]}
                            },
                            "required": ["description", "owner"]
                        }
                    },
                    
                    # Follow-up items
                    "follow_up_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "context": {"type": "string"},
                                "related_topics": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["description"]
                        }
                    },
                    
                    # Deliverable intelligence
                    "deliverables": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string", "enum": ["presentation", "model", "tracker", "analysis", "report", "dashboard", "documentation", "other"]},
                                "target_audience": {"type": "array", "items": {"type": "string"}},
                                "requirements": {"type": "array", "items": {"type": "string"}},
                                "discussed_evolution": {"type": ["string", "null"]},
                                "dependencies": {"type": "array", "items": {"type": "string"}},
                                "deadline": {"type": ["string", "null"]},
                                "format_preferences": {"type": ["string", "null"]}
                            },
                            "required": ["name", "type"]
                        }
                    },
                    
                    # Stakeholder intelligence
                    "stakeholder_intelligence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "stakeholder": {"type": "string"},
                                "role": {"type": ["string", "null"]},
                                "communication_preferences": {"type": ["string", "null"]},
                                "noted_concerns": {"type": "array", "items": {"type": "string"}},
                                "format_preferences": {"type": ["string", "null"]},
                                "questions_asked": {"type": "array", "items": {"type": "string"}},
                                "key_interests": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["stakeholder"]
                        }
                    },
                    
                    # Knowledge graph connections
                    "knowledge_connections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "entity": {"type": "string"},
                                "entity_type": {"type": "string", "enum": ["person", "stakeholder_group", "project", "system", "deliverable", "requirement", "process", "decision", "concept"]},
                                "relationship": {"type": ["string", "null"]},
                                "related_entity": {"type": ["string", "null"]},
                                "context": {"type": ["string", "null"]}
                            },
                            "required": ["entity", "entity_type"]
                        }
                    },
                    
                    # Enhanced metadata
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "topics": {"type": "array", "items": {"type": "string"}},
                            "projects": {"type": "array", "items": {"type": "string"}},
                            "departments": {"type": "array", "items": {"type": "string"}},
                            "systems_discussed": {"type": "array", "items": {"type": "string"}},
                            "source_file": {"type": ["string", "null"]},
                            "related_meetings": {"type": "array", "items": {"type": "string"}},
                            "process_areas": {"type": "array", "items": {"type": "string", "enum": ["order_to_cash", "procure_to_pay", "record_to_report", "hire_to_retire", "other"]}},
                            "meeting_sentiment": {"type": "string", "enum": ["positive", "neutral", "mixed", "negative", "urgent"]},
                            "follow_up_required": {"type": "boolean"}
                        }
                    },
                    
                    # Implementation insights
                    "implementation_insights": {
                        "type": "object",
                        "properties": {
                            "challenges_identified": {"type": "array", "items": {"type": "string"}},
                            "risk_areas": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "risk": {"type": "string"},
                                        "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                                        "mitigation_approach": {"type": ["string", "null"]}
                                    }
                                }
                            },
                            "success_criteria_discussed": {"type": "array", "items": {"type": "string"}},
                            "dependencies_highlighted": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    
                    # Cross-project context
                    "cross_project_context": {
                        "type": "object",
                        "properties": {
                            "related_initiatives": {"type": "array", "items": {"type": "string"}},
                            "shared_resources": {"type": "array", "items": {"type": "string"}},
                            "impact_on_other_projects": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "project": {"type": "string"},
                                        "impact_description": {"type": "string"},
                                        "coordination_needed": {"type": "boolean"}
                                    }
                                }
                            }
                        }
                    },
                    
                    # Client-ready email
                    "client_ready_email": {"type": "string", "description": "A complete, client-facing follow-up email draft."},
                    
                    # Map to our existing schema for compatibility
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
                                            "enum": ["decision", "action", "insight", "discussion", "risk", "deadline"]
                                        },
                                        "importance": {
                                            "type": "string",
                                            "enum": ["high", "medium", "low"]
                                        }
                                    }
                                },
                                "entity_mentions": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    },
                    
                    # Entities for our system
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {
                                    "type": "string",
                                    "enum": ["person", "project", "feature", "deadline", "metric", "team", "system", "technology"]
                                },
                                "current_state": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": ["string", "null"]},
                                        "progress": {"type": ["string", "null"]},
                                        "health": {"type": ["string", "null"]},
                                        "assigned_to": {"type": ["string", "null"]},
                                        "deadline": {"type": ["string", "null"]},
                                        "blockers": {"type": "array", "items": {"type": "string"}}
                                    }
                                },
                                "attributes": {"type": "object"}
                            },
                            "required": ["name", "type"]
                        }
                    },
                    
                    # Relationships for our system
                    "relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from": {"type": "string"},
                                "to": {"type": "string"},
                                "type": {
                                    "type": "string",
                                    "enum": ["owns", "works_on", "reports_to", "depends_on", "blocks", "assigned_to", "responsible_for", "collaborates_with"]
                                },
                                "attributes": {"type": "object"}
                            },
                            "required": ["from", "to", "type"]
                        }
                    }
                },
                "required": [
                    "meeting_title",
                    "meeting_date",
                    "participants",
                    "meeting_id",
                    "executive_summary",
                    "detailed_minutes",
                    "key_decisions",
                    "action_items",
                    "metadata",
                    "memories",
                    "entities",
                    "relationships"
                ]
            }
        }

    def extract(self, transcript: str, meeting_id: str, email_metadata: Optional[Dict[str, Any]] = None) -> ExtractionResult:
        """Extract comprehensive meeting intelligence."""
        try:
            # Add email metadata to prompt if available
            context = f"Extract business intelligence from this transcript:\n\n{transcript}"
            
            if email_metadata:
                context += f"\n\nEmail Context:\n"
                if email_metadata.get("from"):
                    context += f"From: {email_metadata['from']}\n"
                if email_metadata.get("to"):
                    context += f"To: {', '.join(email_metadata['to'])}\n"
                if email_metadata.get("date"):
                    context += f"Date: {email_metadata['date']}\n"
                if email_metadata.get("subject"):
                    context += f"Subject: {email_metadata['subject']}\n"

            # Call LLM with enhanced schema
            # Add schema to the user message for Claude
            schema_str = json.dumps(self.json_schema["schema"], indent=2)
            context_with_schema = f"{context}\n\nRESPOND ONLY WITH VALID JSON. No other text. The JSON must match this exact schema:\n\n{schema_str}\n\nRemember: Start with {{ and end with }}. No explanations."
            
            response = self.client.chat.completions.create(
                model=settings.openrouter_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": context_with_schema}
                ],
                temperature=0.3,
                max_tokens=20000
            )

            # Parse response
            content = response.choices[0].message.content
            logger.info(f"LLM response content: {repr(content)[:200]}")
            logger.info(f"LLM response type: {type(content)}")
            logger.info(f"Full response: {response}")
            
            if not content:
                logger.error("Empty response from LLM")
                raise ValueError("Empty response from LLM")
            data = json.loads(content)
            
            # Convert to our format while preserving all the rich data
            return self._convert_to_extraction_result(data, meeting_id, transcript)
            
        except Exception as e:
            logger.error(f"Enhanced extraction failed: {e}")
            # Fall back to basic extraction
            return self._basic_extraction(transcript, meeting_id)
    
    def _convert_to_extraction_result(self, data: Dict[str, Any], meeting_id: str, transcript: str) -> ExtractionResult:
        """Convert enhanced extraction to our ExtractionResult format."""
        # Convert memories from detailed minutes and key points
        memories = data.get("memories", [])
        
        # Also create memories from key decisions and action items
        for decision in data.get("decisions_with_context", []):
            memories.append({
                "content": f"Decision: {decision['decision']} - Rationale: {decision['rationale']}",
                "metadata": {"type": "decision", "importance": "high"},
                "entity_mentions": decision.get("stakeholders_involved", [])
            })
        
        # Convert to Memory objects
        memory_objects = []
        for mem_data in memories:
            memory = Memory(
                meeting_id=meeting_id,
                content=mem_data["content"],
                speaker=mem_data.get("speaker"),
                timestamp=mem_data.get("timestamp"),
                metadata=mem_data.get("metadata", {}),
                entity_mentions=mem_data.get("entity_mentions", [])
            )
            memory_objects.append(memory)
        
        # Build comprehensive metadata
        metadata = data.get("metadata", {})
        metadata.update({
            "meeting_type": data.get("meeting_type"),
            "meeting_duration": data.get("meeting_duration"),
            "executive_summary_bullets": data.get("executive_summary_bullets", []),
            "deliverables": data.get("deliverables", []),
            "stakeholder_intelligence": data.get("stakeholder_intelligence", []),
            "implementation_insights": data.get("implementation_insights", {}),
            "cross_project_context": data.get("cross_project_context", {}),
            "detailed_summary": data.get("executive_summary", ""),
            "client_email": data.get("client_ready_email", ""),
            "transcript_context": transcript  # Pass full transcript for pattern matching
        })
        
        # Convert participants list to array if string
        participants = data.get("participants", [])
        if isinstance(participants, str):
            participants = [p.strip() for p in participants.split(",")]
        
        return ExtractionResult(
            memories=memory_objects,
            entities=data.get("entities", []),
            relationships=data.get("relationships", []),
            states=[],  # State changes will be detected in post-processing
            meeting_metadata=metadata,
            summary=data.get("executive_summary", ""),
            topics=metadata.get("topics", []),
            participants=participants,
            decisions=data.get("key_decisions", []),
            action_items=data.get("action_items", [])
        )
    
    def _basic_extraction(self, transcript: str, meeting_id: str) -> ExtractionResult:
        """Fallback basic extraction if enhanced fails."""
        # Simple extraction logic
        return ExtractionResult(
            memories=[],
            entities=[],
            relationships=[],
            states=[],
            meeting_metadata={},
            summary="Meeting transcript processed with basic extraction.",
            topics=[],
            participants=[],
            decisions=[],
            action_items=[]
        )