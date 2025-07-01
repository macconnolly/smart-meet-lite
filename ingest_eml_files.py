#!/usr/bin/env python3
"""Parse and ingest all EML files from the data folder."""

import os
import email
import requests
from pathlib import Path
from email import policy
from email.parser import Parser
import re

def extract_text_from_eml(eml_path):
    """Extract text content from an EML file."""
    try:
        with open(eml_path, 'r', encoding='utf-8', errors='ignore') as f:
            msg = email.message_from_file(f, policy=policy.default)
        
        # Extract text content
        text_content = []
        
        # Get subject
        subject = msg.get('subject', '')
        
        # Extract body
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    try:
                        body = part.get_content()
                        if body:
                            text_content.append(body)
                    except:
                        pass
                elif part.get_content_type() == 'text/html':
                    try:
                        # Basic HTML to text conversion
                        html = part.get_content()
                        # Remove HTML tags
                        text = re.sub('<[^<]+?>', '', html)
                        # Clean up whitespace
                        text = ' '.join(text.split())
                        if text:
                            text_content.append(text)
                    except:
                        pass
        else:
            try:
                body = msg.get_content()
                if body:
                    text_content.append(body)
            except:
                pass
        
        # Combine all text
        full_text = '\n'.join(text_content)
        
        # Clean up common email artifacts
        full_text = re.sub(r'From:.*?\n', '', full_text)
        full_text = re.sub(r'To:.*?\n', '', full_text)
        full_text = re.sub(r'Sent:.*?\n', '', full_text)
        full_text = re.sub(r'Subject:.*?\n', '', full_text)
        full_text = re.sub(r'-{3,}.*?-{3,}', '', full_text, flags=re.DOTALL)
        
        # Limit length for API
        if len(full_text) > 10000:
            full_text = full_text[:10000] + "... [truncated]"
        
        return subject, full_text.strip()
    
    except Exception as e:
        print(f"Error parsing {eml_path}: {e}")
        return None, None

def ingest_meeting(title, transcript):
    """Ingest a meeting via the API."""
    try:
        response = requests.post(
            "http://localhost:8000/api/ingest",
            json={
                "title": title,
                "transcript": transcript
            },
            timeout=30
        )
        return response
    except Exception as e:
        return None

# Get all EML files
data_dir = Path("data")
eml_files = list(data_dir.glob("*.eml"))

print(f"Found {len(eml_files)} EML files to process")
print("=" * 60)

successful = 0
failed = 0
errors = []

for i, eml_file in enumerate(eml_files, 1):
    print(f"\n{i}. Processing: {eml_file.name}")
    
    # Extract content
    subject, content = extract_text_from_eml(eml_file)
    
    if not content or len(content) < 50:
        print("   ⚠️  No meaningful content extracted")
        failed += 1
        continue
    
    print(f"   📄 Extracted {len(content)} characters")
    print(f"   📋 Title: {subject or eml_file.stem}")
    
    # Use filename as title if subject is empty
    title = subject or eml_file.stem
    
    # Ingest the meeting
    print("   📤 Sending to API...")
    response = ingest_meeting(title, content)
    
    if response and response.status_code == 200:
        result = response.json()
        print(f"   ✅ Success! Entities: {result['entity_count']}, Memories: {result['memory_count']}")
        successful += 1
    else:
        error_msg = f"Status {response.status_code}" if response else "Connection error"
        print(f"   ❌ Failed: {error_msg}")
        failed += 1
        errors.append({
            "file": eml_file.name,
            "error": error_msg,
            "details": response.text[:200] if response else "No response"
        })

print("\n" + "=" * 60)
print("INGESTION SUMMARY")
print("=" * 60)
print(f"Total files: {len(eml_files)}")
print(f"✅ Successful: {successful}")
print(f"❌ Failed: {failed}")

if errors:
    print("\n🔴 Errors:")
    for err in errors:
        print(f"  - {err['file']}: {err['error']}")

# Get final statistics
print("\n" + "=" * 60)
print("SYSTEM STATISTICS")
print("=" * 60)

try:
    # Get entity count
    response = requests.get("http://localhost:8000/api/entities")
    if response.status_code == 200:
        entities = response.json()
        print(f"Total entities: {len(entities)}")
        
        # Count by type
        entity_types = {}
        for entity in entities:
            etype = entity.get('type', 'unknown')
            entity_types[etype] = entity_types.get(etype, 0) + 1
        
        print("\nEntities by type:")
        for etype, count in sorted(entity_types.items()):
            print(f"  - {etype}: {count}")
    
    # Get analytics
    response = requests.get("http://localhost:8000/api/analytics/entity_counts")
    if response.status_code == 200:
        counts = response.json()
        print(f"\nTotal meetings in system: {counts.get('meetings', 0)}")
        print(f"Total memories extracted: {counts.get('memories', 0)}")

except Exception as e:
    print(f"Error getting statistics: {e}")

print("\n✅ EML ingestion complete!")