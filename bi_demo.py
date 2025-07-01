"""Business Intelligence Demo for Smart-Meet Lite."""

import requests
import json
from datetime import datetime, timedelta
import time


API_URL = "http://localhost:8000"


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def ingest_meeting(title, transcript, date=None):
    """Ingest a meeting and return the response."""
    try:
        payload = {"title": title, "transcript": transcript}
        if date:
            payload["date"] = date.isoformat()

        response = requests.post(f"{API_URL}/api/ingest", json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes

        data = response.json()
        print(f"✓ Ingested: {title}")
        print(f"  - Memories: {data.get('memory_count', 0)}")
        print(f"  - Entities: {data.get('entity_count', 0)}")
        print(f"  - Decisions: {len(data.get('decisions', []))}")
        print(f"  - Action Items: {len(data.get('action_items', []))}")
        return data

    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to ingest {title}: {e}")
        return None
    except json.JSONDecodeError:
        print(f"✗ Failed to decode JSON response for {title}: {response.text}")
        return None


def ask_question(query):
    """Ask a business intelligence question."""
    response = requests.post(f"{API_URL}/api/query", json={"query": query})
    if response.status_code == 200:
        data = response.json()
        print(f"\n❓ Question: {query}")
        print(f"💡 Answer: {data['answer']}")
        print(f"📊 Confidence: {data['confidence']:.1%}")
        print(f"🎯 Intent: {data['intent']['type']}")
        if data["entities_involved"]:
            entities = [e["name"] for e in data["entities_involved"]]
            print(f"🏷️  Entities: {', '.join(entities)}")
        return data
    else:
        print(f"✗ Query failed: {response.text}")
        return None


def run_project_lifecycle_demo():
    """Demonstrate tracking a project through its lifecycle."""
    print_section("PROJECT LIFECYCLE TRACKING DEMO")

    # Meeting 1: Project Kickoff
    print("\n1️⃣  Project Kickoff Meeting")
    ingest_meeting(
        "Mobile App Redesign - Kickoff",
        """
Sarah (Product Manager): Good morning everyone. We're kicking off the mobile app redesign project today.

Mike (Lead Developer): Excited to get started! What's our timeline looking like?

Sarah: We're targeting a Q2 release, so we have about 3 months. Let's break down the major components.

Lisa (UX Designer): I've identified three main areas: navigation overhaul, dark mode support, and performance improvements.

Mike: For the backend, we'll need to optimize our API responses. Current load times are around 3 seconds.

Tom (Frontend Dev): I can take ownership of the navigation redesign. I think React Native's new navigation library will help.

Sarah: Great! Mike, can you own the API optimization? And Lisa, you'll lead the design system updates?

Mike: Absolutely. I'll aim to get response times under 1 second.

Lisa: Yes, I'll have the initial mockups ready by next week.

Sarah: Perfect. Let's set our initial milestones. Design complete by end of month 1, development sprint in month 2, and testing in month 3.

Tom: Should we consider any risks?

Mike: The main risk is our dependency on the legacy billing system. It might slow down the API work.

Sarah: Good point. Let's plan for that. Any other concerns?

Lisa: We should get user feedback early. I'll set up some user testing sessions for week 2.

Sarah: Excellent initiative. Let's meet weekly to track progress. Our success metrics will be: app load time under 1 second, user satisfaction above 4.5 stars, and zero critical bugs at launch.
        """,
        datetime.now() - timedelta(days=60),
    )

    time.sleep(2)

    # Meeting 2: First Progress Update
    print("\n2️⃣  First Progress Update")
    ingest_meeting(
        "Mobile App Redesign - Week 2 Status",
        """
Sarah: Let's get our first status update. Lisa, how are the mockups coming along?

Lisa: I've completed the navigation mockups and initial dark mode designs. User testing revealed some issues with the tab bar - users found it confusing.

Sarah: What changes are you planning?

Lisa: We're moving to a bottom navigation pattern with clearer icons. I'll have updated designs by Friday.

Tom: I've started implementing the new navigation structure. About 20% complete. The new library is working well.

Mike: API optimization is progressing. I've identified the bottlenecks - mainly in our database queries. Currently at 2.1 seconds, down from 3.

Sarah: Good progress. Any blockers?

Mike: Yes, the billing system integration is indeed slowing us down. We need to coordinate with the billing team.

Sarah: I'll set up a meeting with them tomorrow. Tom, any issues on your end?

Tom: No blockers, but I'll need the final designs from Lisa before I can complete the implementation.

Sarah: Lisa, can you prioritize getting Tom what he needs?

Lisa: Will do. I'll have the navigation designs finalized by end of week.

Sarah: Great. We're on track but need to watch that billing system dependency closely.
        """,
        datetime.now() - timedelta(days=46),
    )

    time.sleep(2)

    # Meeting 3: Mid-project Review
    print("\n3️⃣  Mid-Project Review")
    ingest_meeting(
        "Mobile App Redesign - Month 1 Review",
        """
Sarah: We're one month in. Let's review where we stand against our milestones.

Lisa: Design work is 90% complete. All mockups are done, dark mode is fully designed, and we've incorporated user feedback.

Tom: Navigation implementation is now 60% complete. The bottom navigation is working great. Users love it in our beta tests.

Mike: API optimization has hit a snag. We're at 1.5 seconds, but the billing system is preventing further optimization. 

Sarah: That's concerning. What are our options?

Mike: We could cache the billing data, but that adds complexity. Or we could decouple from billing for the initial release.

Sarah: Let's go with caching for now. Can you estimate the additional effort?

Mike: About one extra week of development.

Sarah: Okay, we can absorb that. Tom, will you be done with navigation by end of next week?

Tom: Yes, definitely. I'm actually ahead of schedule.

Lisa: I'm starting to work on the design system documentation so the team can maintain consistency.

Sarah: Excellent. Despite the API challenges, we're in good shape. Let's push hard for the next sprint.

Mike: I'll prioritize the caching implementation. Should have it done by next status meeting.

Sarah: Thanks everyone. We're still on track for Q2 delivery.
        """,
        datetime.now() - timedelta(days=30),
    )

    time.sleep(2)

    # Meeting 4: Pre-release Status
    print("\n4️⃣  Pre-Release Status")
    ingest_meeting(
        "Mobile App Redesign - Pre-Release Check",
        """
Sarah: We're in the final stretch. Two weeks until release. Where do we stand?

Tom: Navigation is 100% complete. All features are implemented and tested.

Mike: API optimization is done! We're consistently under 1 second - averaging 0.8 seconds. The caching solution works perfectly.

Lisa: All design work is complete. The design system is documented and the team is trained.

Sarah: Fantastic! What about testing?

Tom: We've found and fixed 15 bugs. No critical issues remaining.

Mike: Performance testing shows we're exceeding our targets. The app is noticeably faster.

Sarah: User feedback?

Lisa: Latest beta test shows 4.7 star average rating. Users especially love the dark mode and speed improvements.

Sarah: We're exceeding all our success metrics! Any last-minute concerns?

Mike: The billing cache needs to refresh every 24 hours. I've set up monitoring to ensure it's working.

Tom: We should do one more regression test after Mike's final changes.

Sarah: Agreed. Let's do final testing next week and prepare for launch. Great work, everyone!

Lisa: Should we start planning the launch announcement?

Sarah: Yes, let's coordinate with marketing. This is going to be a great release!
        """,
        datetime.now() - timedelta(days=14),
    )

    time.sleep(2)

    # Now ask various business intelligence questions
    print_section("BUSINESS INTELLIGENCE QUERIES")

    questions = [
        "What is the current status of the mobile app redesign project?",
        "Who owns the API optimization work?",
        "How has the API performance improved over time?",
        "What were the main risks identified for the project?",
        "What are the success metrics for the mobile app redesign?",
        "Show me the timeline of the navigation implementation",
        "What decisions were made about the billing system dependency?",
        "Who is responsible for the design system?",
        "What is the current user satisfaction rating?",
        "List all the features being implemented in the mobile app redesign",
    ]

    for question in questions:
        ask_question(question)
        time.sleep(1)


def run_entity_tracking_demo():
    """Demonstrate entity tracking capabilities."""
    print_section("ENTITY TRACKING DEMO")

    # List all entities
    print("📋 Listing all tracked entities...")
    response = requests.get(f"{API_URL}/api/entities")
    if response.status_code == 200:
        entities = response.json()
        for entity in entities[:10]:  # Show first 10
            state = entity.get("current_state", {})
            status = state.get("status", "unknown")
            print(f"  • {entity['name']} ({entity['type']}) - Status: {status}")

    # Get analytics
    print("\n📊 Entity Analytics...")
    response = requests.get(f"{API_URL}/api/analytics/entity_counts")
    if response.status_code == 200:
        data = response.json()
        print("  Entity counts by type:")
        for entity_type, count in data["data"]["by_type"].items():
            print(f"    - {entity_type}: {count}")


def run_search_demo():
    """Demonstrate semantic search with entity filtering."""
    print_section("SEMANTIC SEARCH DEMO")

    # Simple search
    print("🔍 Searching for 'performance improvements'...")
    response = requests.post(
        f"{API_URL}/api/search", json={"query": "performance improvements", "limit": 3}
    )

    if response.status_code == 200:
        results = response.json()
        print(f"Found {results['count']} results:")
        for i, result in enumerate(results["results"], 1):
            print(f"\n  {i}. {result['memory']['content']}")
            print(f"     Speaker: {result['memory']['speaker']}")
            print(f"     Score: {result['score']:.3f}")

    # Search with entity filter
    print("\n🔍 Searching for 'progress' in Mobile App Redesign context...")
    response = requests.post(
        f"{API_URL}/api/search",
        json={
            "query": "progress",
            "entity_filter": ["Mobile App Redesign"],
            "limit": 3,
        },
    )

    if response.status_code == 200:
        results = response.json()
        print(f"Found {results['count']} results with entity filter")


def main():
    """Run all demos."""
    print("🚀 Smart-Meet Lite Business Intelligence Demo")
    print("=" * 60)

    # Check if API is running
    time.sleep(5)  # Wait for API to start
    time.sleep(5)  # Wait for API to start
    try:
        response = requests.get(API_URL)
        if response.status_code != 200:
            print("✗ API is not running. Start it with: python -m src.api")
            return
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to API. Start it with: python -m src.api")
        return

    # Run demos
    run_project_lifecycle_demo()
    time.sleep(2)

    run_entity_tracking_demo()
    time.sleep(2)

    run_search_demo()

    print("\n" + "=" * 60)
    print("✅ Demo completed!")
    print("\nYou can now:")
    print("1. Ask more questions using the /api/query endpoint")
    print("2. Explore entity timelines with /api/entities/{id}/timeline")
    print("3. View analytics at /api/analytics/{metric}")
    print("4. Access the interactive API docs at http://localhost:8000/docs")


if __name__ == "__main__":
    main()
