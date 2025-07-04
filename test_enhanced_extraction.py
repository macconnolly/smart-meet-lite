"""Test enhanced extraction with comprehensive schema."""

import asyncio
import httpx
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

# Sample meeting transcript with rich content
SAMPLE_TRANSCRIPT = """
From: john.smith@acme.com
To: sarah.johnson@acme.com, mike.wilson@acme.com
CC: emily.chen@acme.com
Date: 2025-01-02 10:00 AM
Subject: UAT Testing Planning - System Inventory Alignment

Meeting Notes - UAT Testing Coordination

Participants: John Smith (Project Lead), Sarah Johnson (Tech Lead), Mike Wilson (Business Analyst), Emily Chen (QA Manager)

Executive Summary:
We aligned on the UAT testing approach for the Athens separation project. Key decisions were made regarding system inventory mapping, testing timelines, and resource allocation. The team identified critical risks around data migration dependencies and agreed on mitigation strategies.

Agenda Items Discussed:

1. System Inventory Mapping
- Sarah presented the current state of system inventory with 47 applications identified
- Mike raised concerns about vendor systems not being fully documented
- Decision: Create comprehensive vendor system matrix by Jan 10th
- Emily will coordinate with procurement to get vendor contact details

2. UAT Timeline and Milestones
- Current timeline shows UAT starting Jan 15th
- John highlighted that the mobile app redesign project is now in progress (was previously planned)
- Risk identified: Data migration testing may block UAT progress
- Mitigation: Run parallel tracks for UI testing and data validation

3. Resource Allocation
- Need 5 additional testers for peak UAT period (Jan 20-30)
- Sarah's team can provide 2 developers for test support
- Decision: Hire 3 contract testers with banking domain experience
- Budget impact: $45K for 6-week engagement

4. Testing Strategy
- Emily proposed risk-based testing approach focusing on critical workflows
- Mike wants comprehensive testing of all customer touchpoints
- Compromise: Tier 1 systems get full regression, Tier 2 get smoke tests
- Decision ratified by John with caveat that payment systems are all Tier 1

5. Deliverables Discussion
- Test Plan document needs executive formatting for steering committee
- Sarah prefers technical details in appendix, executives want 2-page summary
- Dashboard requirements: Real-time test execution metrics, defect trends
- Mike asked: "Can we get automated daily reports?" - Emily confirmed yes

Action Items:
1. Create vendor system matrix - Mike Wilson - Jan 10th
2. Hire contract testers - Emily Chen - Jan 8th  
3. Prepare executive test plan - Sarah Johnson - Jan 5th
4. Set up automated reporting - Emily Chen - Jan 12th

Risks Identified:
- Data migration dependencies could delay UAT start (High severity)
- Vendor system documentation gaps (Medium severity)
- Resource availability during holiday period (Low severity)

Next Steps:
Follow-up meeting scheduled for Jan 5th to review test plan draft and vendor matrix progress.
"""


async def test_enhanced_extraction():
    """Test the enhanced extraction capabilities."""
    async with httpx.AsyncClient() as client:
        # Test 1: Ingest meeting with enhanced extraction
        print("1. Testing enhanced meeting ingestion...")
        
        ingest_data = {
            "title": "UAT Testing Planning - System Inventory Alignment",
            "transcript": SAMPLE_TRANSCRIPT,
            "date": datetime.now().isoformat(),
            "email_metadata": {
                "from": "john.smith@acme.com",
                "to": ["sarah.johnson@acme.com", "mike.wilson@acme.com"],
                "cc": ["emily.chen@acme.com"],
                "date": "2025-01-02T10:00:00",
                "subject": "UAT Testing Planning - System Inventory Alignment"
            }
        }
        
        response = await client.post(
            f"{API_BASE}/api/ingest",
            json=ingest_data,
            timeout=60.0
        )
        
        if response.status_code == 200:
            result = response.json()
            meeting_id = result["id"]
            print(f"✓ Meeting ingested successfully: {meeting_id}")
            print(f"  - Memories: {result['memory_count']}")
            print(f"  - Entities: {result['entity_count']}")
            print(f"  - Summary: {result['summary'][:100]}...")
        else:
            print(f"✗ Ingestion failed: {response.status_code}")
            print(response.text)
            return
        
        # Test 2: Get comprehensive intelligence
        print("\n2. Testing intelligence retrieval...")
        
        response = await client.get(
            f"{API_BASE}/api/meetings/{meeting_id}/intelligence"
        )
        
        if response.status_code == 200:
            intelligence = response.json()
            
            print(f"✓ Intelligence retrieved successfully")
            print(f"\nDeliverables tracked: {len(intelligence['intelligence']['deliverables'])}")
            for deliverable in intelligence['intelligence']['deliverables']:
                print(f"  - {deliverable['name']} ({deliverable['type']})")
                if deliverable.get('format_preferences'):
                    print(f"    Format: {deliverable['format_preferences']}")
            
            print(f"\nStakeholder intelligence: {len(intelligence['intelligence']['stakeholder_intelligence'])}")
            for stakeholder in intelligence['intelligence']['stakeholder_intelligence']:
                print(f"  - {stakeholder['stakeholder']} ({stakeholder.get('role', 'Unknown role')})")
                if stakeholder.get('questions_asked'):
                    print(f"    Questions: {stakeholder['questions_asked']}")
            
            print(f"\nDecisions with context: {len(intelligence['intelligence']['decisions_with_context'])}")
            for decision in intelligence['intelligence']['decisions_with_context']:
                print(f"  - {decision['decision']}")
                print(f"    Rationale: {decision.get('rationale', 'Not specified')}")
                print(f"    Status: {decision.get('decision_status', 'Unknown')}")
            
            print(f"\nRisks identified: {len(intelligence['intelligence']['risk_areas'])}")
            for risk in intelligence['intelligence']['risk_areas']:
                print(f"  - {risk['risk']} (Severity: {risk['severity']})")
                if risk.get('mitigation_approach'):
                    print(f"    Mitigation: {risk['mitigation_approach']}")
        else:
            print(f"✗ Intelligence retrieval failed: {response.status_code}")
            print(response.text)
        
        # Test 3: Check state tracking
        print("\n3. Testing state tracking...")
        
        # Query for state changes
        response = await client.post(
            f"{API_BASE}/api/query",
            json={"query": "What's the status of the mobile app redesign project?"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ State query successful")
            print(f"  Answer: {result['answer']}")
            print(f"  Confidence: {result['confidence']}")
        else:
            print(f"✗ State query failed: {response.status_code}")


if __name__ == "__main__":
    print("Testing Enhanced Meeting Extraction")
    print("=" * 50)
    asyncio.run(test_enhanced_extraction())