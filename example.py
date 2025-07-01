"""Simple usage examples for Smart-Meet Lite."""

import requests


API_URL = "http://localhost:8000"


def example_ingest():
    """Example of ingesting a meeting."""
    print("\n1. Ingesting a meeting transcript...")

    response = requests.post(
        f"{API_URL}/api/ingest",
        json={
            "title": "Team Standup - Sprint 23",
            "transcript": """
John: Good morning team. Let's do our standup.

Sarah: I'll go first. Yesterday I completed the user authentication feature. It's using OAuth2 as we discussed. Today I'm starting on the password reset functionality.

John: Great progress! Any blockers?

Sarah: No blockers, but I'll need the email service credentials to test the password reset emails.

Mike: I can help with that. I finished setting up the email service yesterday. I'll send you the credentials after this meeting.

John: Perfect. Mike, what about your tasks?

Mike: I've been working on the API rate limiting. It's about 70% done. We're using Redis for the rate limit counters. Should be complete by tomorrow.

Lisa: For the frontend, I've integrated Sarah's authentication API. The login flow is working smoothly. Today I'm adding the remember me functionality and improving the error messages.

John: Excellent! Any risks we should be aware of?

Mike: The Redis cluster might need scaling if we hit high traffic. I'll monitor it closely.

Sarah: Also, we should plan for a security review before going live with authentication.

John: Good points. I'll schedule a security review for next week. Let's keep pushing forward. Great work everyone!
""",
        },
    )

    if response.status_code == 200:
        data = response.json()
        print("✓ Meeting ingested successfully!")
        print(f"  ID: {data['id']}")
        print(f"  Entities found: {data['entity_count']}")
        print(f"  Memories extracted: {data['memory_count']}")
        return data["id"]
    else:
        print(f"✗ Error: {response.text}")
        return None


def example_search():
    """Example of searching memories."""
    print("\n2. Searching for information...")

    response = requests.post(
        f"{API_URL}/api/search",
        json={"query": "authentication OAuth security", "limit": 5},
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Found {data['count']} relevant memories:")
        for i, result in enumerate(data["results"], 1):
            print(f"\n  {i}. {result['memory']['content']}")
            print(f"     Relevance: {result['score']:.1%}")


def example_query():
    """Example of business intelligence queries."""
    print("\n3. Asking business intelligence questions...")

    questions = [
        "What is Sarah working on?",
        "Who is responsible for the email service?",
        "What's the status of API rate limiting?",
        "What risks were identified?",
    ]

    for question in questions:
        response = requests.post(f"{API_URL}/api/query", json={"query": question})

        if response.status_code == 200:
            data = response.json()
            print(f"\n❓ {question}")
            print(f"💡 {data['answer']}")


def example_entities():
    """Example of viewing entities."""
    print("\n4. Viewing tracked entities...")

    response = requests.get(f"{API_URL}/api/entities")

    if response.status_code == 200:
        entities = response.json()
        print(f"✓ Found {len(entities)} entities:")

        # Group by type
        by_type = {}
        for entity in entities:
            entity_type = entity["type"]
            if entity_type not in by_type:
                by_type[entity_type] = []
            by_type[entity_type].append(entity["name"])

        for entity_type, names in by_type.items():
            print(f"\n  {entity_type.upper()}:")
            for name in names[:5]:  # Show first 5
                print(f"    • {name}")


def main():
    """Run examples."""
    print("=" * 60)
    print("Smart-Meet Lite - Simple Examples")
    print("=" * 60)

    # Check API
    try:
        response = requests.get(API_URL)
        if response.status_code != 200:
            print("✗ API is not running. Start it with: python -m src.api")
            return
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot connect to API: {e}")
        print("  Please ensure the API server is running: make dev")
        return

    # Run examples
    meeting_id = example_ingest()

    if meeting_id:
        example_search()
        example_query()
        example_entities()

    print("\n" + "=" * 60)
    print("✅ Examples completed!")
    print("\nTry the business intelligence demo for more advanced features:")
    print("  python bi_demo.py")


if __name__ == "__main__":
    main()
