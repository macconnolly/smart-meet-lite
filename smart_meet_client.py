"""
Smart-Meet Lite Client - Helper functions for easy interaction with the API.

Usage:
    from smart_meet_client import SmartMeetClient
    
    client = SmartMeetClient()
    
    # Ingest a meeting
    meeting = client.ingest_meeting("Team Standup", transcript)
    
    # Ask a question
    answer = client.ask("Who owns the payment feature?")
    
    # Search memories
    results = client.search("API optimization")
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime


class SmartMeetClient:
    """Simple client for Smart-Meet Lite API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize client with API base URL."""
        self.base_url = base_url
        self._check_connection()

    def _check_connection(self):
        """Check if API is reachable."""
        try:
            response = requests.get(f"{self.base_url}/")
            if response.status_code != 200:
                print(f"⚠️  Warning: API returned status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to API. Make sure it's running:")
            print("   python -m src.api")

    def ingest_meeting(
        self, title: str, transcript: str, date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Ingest a meeting transcript.

        Args:
            title: Meeting title
            transcript: Meeting transcript text
            date: Optional meeting date

        Returns:
            Meeting data including extracted entities and memories
        """
        payload = {"title": title, "transcript": transcript}
        if date:
            payload["date"] = date.isoformat()

        response = requests.post(f"{self.base_url}/api/ingest", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Ingested '{title}':")
            print(f"   - {data['memory_count']} memories extracted")
            print(f"   - {data['entity_count']} entities tracked")
            print(f"   - {len(data['decisions'])} decisions identified")
            return data
        else:
            print(f"❌ Failed to ingest: {response.text}")
            return {}

    def ingest_file(
        self, file_path: str, title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest a meeting from a text file.

        Args:
            file_path: Path to transcript file
            title: Optional title (uses filename if not provided)

        Returns:
            Meeting data
        """
        with open(file_path, "r", encoding="utf-8") as f:
            files = {"file": f}
            data = {"title": title} if title else {}

            response = requests.post(
                f"{self.base_url}/api/ingest/file", files=files, data=data
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Ingested file '{file_path}'")
                return result
            else:
                print(f"❌ Failed to ingest file: {response.text}")
                return {}

    def ask(self, question: str) -> str:
        """
        Ask a business intelligence question.

        Args:
            question: Natural language question

        Returns:
            Answer string
        """
        response = requests.post(f"{self.base_url}/api/query", json={"query": question})

        if response.status_code == 200:
            data = response.json()
            confidence = data["confidence"]
            answer = data["answer"]

            print(f"❓ {question}")
            print(f"💡 {answer}")
            print(f"📊 Confidence: {confidence:.0%}")

            return answer
        else:
            print(f"❌ Query failed: {response.text}")
            return "Unable to answer question."

    def search(
        self, query: str, limit: int = 5, entity_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant memories.

        Args:
            query: Search query
            limit: Maximum results
            entity_filter: Optional list of entity names to filter by

        Returns:
            List of search results
        """
        payload = {"query": query, "limit": limit}
        if entity_filter:
            payload["entity_filter"] = entity_filter

        response = requests.post(f"{self.base_url}/api/search", json=payload)

        if response.status_code == 200:
            data = response.json()
            results = data["results"]

            print(f"🔍 Found {len(results)} results for '{query}':")
            for i, result in enumerate(results, 1):
                memory = result["memory"]
                print(f"\n{i}. {memory['content']}")
                if memory["speaker"]:
                    print(f"   Speaker: {memory['speaker']}")
                print(f"   Score: {result['score']:.2f}")

            return results
        else:
            print(f"❌ Search failed: {response.text}")
            return []

    def list_entities(
        self, entity_type: Optional[str] = None, search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List tracked entities.

        Args:
            entity_type: Filter by type (person, project, feature, etc.)
            search: Search term

        Returns:
            List of entities
        """
        params = {}
        if entity_type:
            params["entity_type"] = entity_type
        if search:
            params["search"] = search

        response = requests.get(f"{self.base_url}/api/entities", params=params)

        if response.status_code == 200:
            entities = response.json()

            print(f"📋 Found {len(entities)} entities:")

            # Group by type
            by_type = {}
            for entity in entities:
                etype = entity["type"]
                if etype not in by_type:
                    by_type[etype] = []
                by_type[etype].append(entity)

            for etype, items in by_type.items():
                print(f"\n{etype.upper()}:")
                for entity in items[:5]:  # Show first 5
                    state = entity.get("current_state", {})
                    status = state.get("status", "unknown")
                    print(f"  • {entity['name']} - {status}")

            return entities
        else:
            print(f"❌ Failed to list entities: {response.text}")
            return []

    def get_timeline(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Get timeline for an entity.

        Args:
            entity_name: Name of the entity

        Returns:
            Timeline of state changes
        """
        # First, find the entity
        entities = requests.get(
            f"{self.base_url}/api/entities", params={"search": entity_name}
        ).json()

        if not entities:
            print(f"❌ Entity '{entity_name}' not found")
            return []

        entity_id = entities[0]["id"]

        # Get timeline
        response = requests.get(f"{self.base_url}/api/entities/{entity_id}/timeline")

        if response.status_code == 200:
            data = response.json()
            timeline = data["timeline"]

            print(f"📅 Timeline for '{entity_name}':")
            for event in timeline:
                print(f"\n• {event['meeting_title']} ({event['timestamp']})")
                print(f"  Changed: {', '.join(event['changed_fields'])}")
                if event["reason"]:
                    print(f"  Reason: {event['reason']}")

            return timeline
        else:
            print(f"❌ Failed to get timeline: {response.text}")
            return []

    def get_analytics(self, metric: str = "entity_counts") -> Dict[str, Any]:
        """
        Get analytics data.

        Args:
            metric: Metric type (entity_counts, state_changes, relationship_network)

        Returns:
            Analytics data
        """
        response = requests.get(f"{self.base_url}/api/analytics/{metric}")

        if response.status_code == 200:
            data = response.json()

            print(f"📊 Analytics - {metric}:")
            if metric == "entity_counts":
                for entity_type, count in data["data"]["by_type"].items():
                    print(f"  {entity_type}: {count}")

            return data
        else:
            print(f"❌ Failed to get analytics: {response.text}")
            return {}

    def quick_demo(self):
        """Run a quick demonstration."""
        print("🎯 Smart-Meet Lite Quick Demo")
        print("=" * 50)

        # Sample transcript
        transcript = """
Sarah (Product Manager): Let's review the payment integration status.

John (Developer): I've completed 75% of the payment API. The basic flow is working.

Sarah: Great progress! What's left to do?

John: Need to implement webhook handling and add retry logic for failed payments.

Mike (QA Engineer): I'll need at least 3 days for testing once John is done.

Sarah: Any blockers?

John: We're waiting on the API credentials from the payment provider.

Sarah: I'll follow up with them today. Let's target end of week for completion.

Mike: I'll prepare the test cases in parallel so we're ready.

Sarah: Perfect. This is high priority for our Q4 release.
"""

        # Ingest the meeting
        print("\n1️⃣ Ingesting sample meeting...")
        meeting = self.ingest_meeting("Payment Integration Review", transcript)

        if meeting:
            print("\n2️⃣ Asking business intelligence questions...")

            # Ask various questions
            questions = [
                "What's the status of the payment integration?",
                "Who is working on the payment API?",
                "What are the blockers?",
                "When will testing begin?",
            ]

            for q in questions:
                print("\n" + "-" * 50)
                self.ask(q)
                input("\nPress Enter for next question...")

            print("\n3️⃣ Searching for specific information...")
            self.search("testing", limit=3)

            print("\n4️⃣ Viewing tracked entities...")
            self.list_entities()

            print("\n" + "=" * 50)
            print("✅ Demo complete!")
            print("\nTry asking your own questions with: client.ask('your question')")


# Convenience functions for quick usage
def quick_start():
    """Quick start guide."""
    print(
        """
Smart-Meet Lite Client - Quick Start

1. Import and create client:
   from smart_meet_client import SmartMeetClient
   client = SmartMeetClient()

2. Ingest a meeting:
   client.ingest_meeting("Meeting Title", "transcript text...")
   # or from file:
   client.ingest_file("meeting.txt")

3. Ask questions:
   client.ask("What's the status of the payment feature?")
   client.ask("Who owns the authentication module?")

4. Search memories:
   client.search("deployment issues")
   client.search("api", entity_filter=["Payment System"])

5. View entities:
   client.list_entities()
   client.list_entities(entity_type="project")
   
6. Get timeline:
   client.get_timeline("Payment API")

Run demo: client.quick_demo()
"""
    )


if __name__ == "__main__":
    # Run quick demo when executed directly
    client = SmartMeetClient()
    client.quick_demo()
