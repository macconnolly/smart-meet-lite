"""Enhanced LLM-based extraction with comprehensive management consultant schema."""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
from openai import OpenAI
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

    def __init__(self, llm_client: OpenAI):
        """Initialize with shared LLM client."""
        # We receive the OpenAI client but will use direct requests instead
        # This maintains compatibility with the API initialization
        self.client = llm_client  # Keep for potential future use
        
        self.system_prompt = """You are an expert meeting analyst. Analyze the transcript and extract structured information.

Focus on:
1. **Key Information**: Decisions, action items, and important discussions
2. **Entities**: People, projects, features, deadlines, systems mentioned
3. **Relationships**: How entities relate to each other (who owns what, dependencies)
4. **Context**: Meeting metadata, topics discussed, follow-up needed

CRITICAL ENTITY NAMING AND TYPE RULES:
- ALWAYS check the "Existing Entities in System" list FIRST
- If an entity is listed there, use the EXACT name and type from that list
- NEVER create variations like "API Migration feature" if "API Migration" already exists
- For NEW entities not in the list:
  - Use the core name WITHOUT suffixes (e.g., "API Migration" not "API Migration feature")
  - For projects: Use the base name (e.g., "Database Upgrade" not "Database Upgrade project")
  - Be consistent: if it's "Project Alpha" in one place, don't use "project alpha" elsewhere
  - Remove redundant descriptors: "feature", "project", "system", "module" unless they're part of the official name

ENTITY TYPE CLASSIFICATION:
- "project": Major initiatives with multiple features/tasks (e.g., "Project Alpha", "Database Upgrade")
- "feature": Specific functionality or component within a project (e.g., "Login System", "Payment Gateway")
- "person": Individual team members (e.g., "Alice", "Bob")
- "deadline": Specific dates or timeframes
- "system": External systems or platforms (e.g., "AWS", "Kubernetes")

IMPORTANT: If something like "API Migration" is mentioned as both a feature and a project in different contexts, classify it consistently based on its primary nature. When in doubt, prefer "project" for larger initiatives.

PROGRESS AND BLOCKERS EXTRACTION:
- For "progress": Extract specific percentage completion (e.g., "30%", "50% complete") or phase descriptions (e.g., "initial design", "testing phase")
- For "blockers": Extract specific issues preventing progress as an array (e.g., ["waiting for vendor credentials", "resource constraints", "technical debt"])
- If no progress is mentioned, use null
- If no blockers exist, use an empty array []

Examples:
- "Project Alpha is now at 50% completion" → progress: "50%"
- "API Migration is blocked, waiting for vendor credentials" → blockers: ["waiting for vendor credentials"]
- "Database Upgrade has moved from planning to in progress" → progress: "in progress phase" (or null if not specific)
- "Project Beta is blocked due to resource constraints" → blockers: ["resource constraints"]

Guidelines:
- Capture the speaker for each memory when identifiable
- Extract actionable items with clear owners
- Identify entity relationships (owns, works_on, depends_on, etc.)
- Always extract progress percentages when mentioned
- Always capture blockers when entities are described as blocked
- Keep content concise but complete

Extract what's available without forcing fields. Quality over quantity."""

        # Simplified JSON schema with proper additionalProperties
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
                    "meeting_id": {"type": "string"},
                    "meeting_type": {"type": "string"},
                    
                    # Summary
                    "executive_summary": {"type": "string"},
                    "key_decisions": {"type": "array", "items": {"type": "string"}},
                    
                    # Action items - simplified
                    "action_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "owner": {"type": "string"},
                                "due_date": {"type": ["string", "null"]},
                                "priority": {"type": "string"},
                                "status": {"type": "string"}
                            },
                            "required": ["description", "owner", "due_date", "priority", "status"],
                            "additionalProperties": False
                        }
                    },
                    
                    # Simplified metadata
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "topics": {"type": "array", "items": {"type": "string"}},
                            "projects": {"type": "array", "items": {"type": "string"}},
                            "risks": {"type": "array", "items": {"type": "string"}},
                            "follow_up_required": {"type": "boolean"}
                        },
                        "required": ["topics", "projects", "risks", "follow_up_required"],
                        "additionalProperties": False
                    },
                    
                    # Memories for our system
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
                                        "type": {"type": "string"},
                                        "importance": {"type": "string"}
                                    },
                                    "required": ["type", "importance"],
                                    "additionalProperties": False
                                },
                                "entity_mentions": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["content", "speaker", "timestamp", "metadata", "entity_mentions"],
                            "additionalProperties": False
                        }
                    },
                    
                    # Entities for our system
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "current_state": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": ["string", "null"]},
                                        "assigned_to": {"type": ["string", "null"]},
                                        "deadline": {"type": ["string", "null"]},
                                        "progress": {"type": ["string", "null"]},
                                        "blockers": {"type": "array", "items": {"type": "string"}}
                                    },
                                    "required": ["status", "assigned_to", "deadline", "progress", "blockers"],
                                    "additionalProperties": False
                                }
                            },
                            "required": ["name", "type", "current_state"],
                            "additionalProperties": False
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
                                "type": {"type": "string"}
                            },
                            "required": ["from", "to", "type"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": [
                    "meeting_title",
                    "meeting_date",
                    "participants",
                    "meeting_id",
                    "meeting_type",
                    "executive_summary",
                    "key_decisions",
                    "action_items",
                    "metadata",
                    "memories",
                    "entities",
                    "relationships"
                ],
                "additionalProperties": False
            }
        }

    def _get_proxies(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration from settings."""
        if settings.https_proxy or settings.http_proxy:
            proxies = {}
            if settings.http_proxy:
                proxies["http"] = settings.http_proxy
            if settings.https_proxy:
                proxies["https"] = settings.https_proxy
            return proxies
        return None

    def extract(self, transcript: str, meeting_id: str, email_metadata: Optional[Dict[str, Any]] = None, existing_entities: Optional[List[Entity]] = None) -> ExtractionResult:
        """Extract comprehensive meeting intelligence."""
        try:
            # Build context with existing entities
            context = "Extract business intelligence from this transcript.\n\n"
            
            # Add existing entities to ensure consistency
            if existing_entities:
                context += "IMPORTANT - Existing Entities in System:\n"
                context += "When these entities are mentioned in the transcript, use the EXACT name and type listed here:\n\n"
                
                # Group by type for clarity
                entities_by_type = {}
                for entity in existing_entities:
                    if entity.type not in entities_by_type:
                        entities_by_type[entity.type] = []
                    entities_by_type[entity.type].append(entity)
                
                for entity_type, entities in entities_by_type.items():
                    context += f"{entity_type.value.upper()}S:\n"
                    for entity in entities:
                        context += f"  - {entity.name}\n"
                context += "\n"
            
            context += f"Transcript:\n{transcript}"
            
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

            # Create request body with proper response_format
            request_body = {
                "model": settings.clean_openrouter_model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": context}
                ],
                "temperature": 0.3,
                "max_tokens": 20000,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": self.json_schema
                }
            }
            
            # Make direct HTTP request to OpenRouter
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "Smart-Meet Lite"
                },
                json=request_body,
                timeout=30.0,
                verify=False,  # Disable SSL verification as requested
                proxies=self._get_proxies()
            )

            # Parse HTTP response
            response.raise_for_status()  # Raise exception for HTTP errors
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]
            logger.info(f"LLM response content: {repr(content)[:200]}")
            logger.info(f"LLM response type: {type(content)}")
            logger.info(f"Full response: {response_data}")
            
            if not content:
                logger.error("Empty response from LLM")
                raise ValueError("Empty response from LLM")
            data = json.loads(content)
            
            # Convert to our format while preserving all the rich data
            return self._convert_to_extraction_result(data, meeting_id, transcript)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error(f"Authentication failed: {e}")
                logger.error("Check your OPENROUTER_API_KEY in .env file")
                result = self._basic_extraction(transcript, meeting_id)
                result.meeting_metadata["extraction_error"] = f"Authentication failed: {str(e)}"
                result.meeting_metadata["error_type"] = "auth_error"
                return result
            elif e.response.status_code == 400:
                logger.error(f"Bad Request: {e}")
                logger.error(f"Model name being used: '{settings.clean_openrouter_model}'")
                logger.error(f"Raw model config: '{settings.openrouter_model}'")
                logger.error(f"Response: {e.response.text[:500] if e.response.text else 'N/A'}")
                result = self._basic_extraction(transcript, meeting_id)
                result.meeting_metadata["extraction_error"] = f"Bad request: {str(e)}"
                result.meeting_metadata["error_type"] = "bad_request"
                result.meeting_metadata["model_attempted"] = settings.clean_openrouter_model
                return result
            else:
                # Re-raise for other HTTP errors
                logger.error(f"HTTP Error {e.response.status_code}: {e}")
                logger.error(f"Response: {e.response.text[:500] if e.response.text else 'N/A'}")
                result = self._basic_extraction(transcript, meeting_id)
                result.meeting_metadata["extraction_error"] = f"HTTP {e.response.status_code}: {str(e)}"
                result.meeting_metadata["error_type"] = "http_error"
                return result
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            result = self._basic_extraction(transcript, meeting_id)
            result.meeting_metadata["extraction_error"] = f"Request failed: {str(e)}"
            result.meeting_metadata["error_type"] = "connection_error"
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response content: {content[:500] if 'content' in locals() else 'N/A'}")
            result = self._basic_extraction(transcript, meeting_id)
            result.meeting_metadata["extraction_error"] = f"JSON parse error: {str(e)}"
            result.meeting_metadata["error_type"] = "parse_error"
            return result
            
        except Exception as e:
            logger.error(f"Unexpected extraction error: {type(e).__name__}: {e}")
            logger.error(f"Full exception: ", exc_info=True)
            # Generic fallback
            result = self._basic_extraction(transcript, meeting_id)
            result.meeting_metadata["extraction_error"] = f"{type(e).__name__}: {str(e)}"
            result.meeting_metadata["error_type"] = "unknown_error"
            return result
    
    def _convert_to_extraction_result(self, data: Dict[str, Any], meeting_id: str, transcript: str) -> ExtractionResult:
        """Convert simplified extraction to our ExtractionResult format."""
        # Convert memories from LLM extraction
        memories = data.get("memories", [])
        
        # Also create memories from key decisions
        for decision in data.get("key_decisions", []):
            memories.append({
                "content": f"Decision: {decision}",
                "metadata": {"type": "decision", "importance": "high"},
                "entity_mentions": []
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
        
        # Build metadata
        metadata = data.get("metadata", {})
        metadata.update({
            "meeting_type": data.get("meeting_type", "general"),
            "detailed_summary": data.get("executive_summary", ""),
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
        """Fallback extraction with heuristic-based parsing - produces usable data."""
        logger.warning("Using basic extraction fallback - enhanced extraction failed")
        
        import re
        from datetime import datetime
        
        # Extract speakers and content using regex
        speaker_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*(?:\([^)]+\))?\s*:'
        memories = []
        entities_found = {}
        speakers = set()
        
        # Split transcript into speaker segments
        segments = re.split(speaker_pattern, transcript)
        
        # Process segments (odd indices are speakers, even are content)
        for i in range(1, len(segments)-1, 2):
            if i+1 < len(segments):
                speaker = segments[i].strip()
                content = segments[i+1].strip()
                
                if speaker and content and len(content) > 10:
                    speakers.add(speaker)
                    
                    # Create memory for substantial content
                    if len(content) >= 30:
                        memory = Memory(
                            content=content[:500],  # Limit length
                            speaker=speaker,
                            meeting_id=meeting_id,
                            metadata={"extraction_method": "basic"},
                            entity_mentions=[]
                        )
                        memories.append(memory)
                    
                    # Extract potential entities (capitalized multi-word phrases)
                    entity_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
                    for match in re.finditer(entity_pattern, content):
                        entity_name = match.group(1)
                        # Filter out common words and speaker names
                        if (len(entity_name) > 3 and 
                            entity_name not in speakers and
                            entity_name not in ['The', 'This', 'That', 'These', 'Those']):
                            entities_found[entity_name] = entities_found.get(entity_name, 0) + 1
        
        # Convert to entity objects
        entities = []
        for name, count in entities_found.items():
            if count >= 2:  # Mentioned at least twice
                # Try to guess entity type
                entity_type = "project"
                if any(word in name.lower() for word in ['api', 'system', 'app', 'service']):
                    entity_type = "feature"
                elif any(word in name.lower() for word in ['team', 'department', 'group']):
                    entity_type = "team"
                
                entities.append({
                    "name": name,
                    "type": entity_type,
                    "attributes": {
                        "mention_count": count,
                        "extraction_method": "basic"
                    }
                })
        
        # Extract basic action items
        action_items = []
        action_patterns = [
            r'(?:will|going to|need to|should|must)\s+(\w+\s+.{10,50})',
            r'(?:action|todo|task):\s*(.+?)(?:\.|$)',
            r'(?:I\'ll|We\'ll)\s+(.+?)(?:\.|$)'
        ]
        
        for pattern in action_patterns:
            for match in re.finditer(pattern, transcript, re.IGNORECASE):
                action_text = match.group(1).strip()
                if len(action_text) > 10:
                    action_items.append({
                        "action": action_text[:100],
                        "owner": "unassigned",
                        "status": "pending"
                    })
        
        # Extract topics based on repeated phrases
        topics = []
        for entity_name, count in entities_found.items():
            if count >= 3:
                topics.append(entity_name)
        
        # Ensure we have at least some data
        if not memories:
            # Create at least one memory from the transcript
            memories.append(Memory(
                content=transcript[:500],
                speaker="Unknown",
                meeting_id=meeting_id,
                metadata={"extraction_method": "basic", "full_transcript": True},
                entity_mentions=[]
            ))
        
        return ExtractionResult(
            memories=memories[:50],  # Limit to 50 memories
            entities=entities[:20],  # Limit to 20 entities  
            relationships=[],
            states=[],
            meeting_metadata={
                "extraction_method": "basic_fallback",
                "warning": "Enhanced extraction failed - using basic heuristics",
                "transcript_length": len(transcript),
                "extraction_timestamp": datetime.now().isoformat()
            },
            summary=f"Basic extraction: Found {len(memories)} statements from {len(speakers)} participants discussing {len(entities)} topics",
            topics=topics[:5] or ["General Discussion"],
            participants=list(speakers) or ["Unknown Participants"],
            decisions=[],
            action_items=action_items[:10]
        )