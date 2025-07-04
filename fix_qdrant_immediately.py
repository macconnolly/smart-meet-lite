#!/usr/bin/env python3
"""
EMERGENCY FIX: Resolve Qdrant version mismatch
Run this to fix the critical blocker preventing queries from working.
"""

import subprocess
import sys
import time

def main():
    print("🚨 EMERGENCY FIX: Qdrant Version Mismatch")
    print("=" * 50)
    
    # Step 1: Update requirements.txt
    print("\n1️⃣ Updating requirements.txt...")
    try:
        with open('requirements.txt', 'r') as f:
            lines = f.readlines()
        
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith('qdrant-client=='):
                old_version = line.strip()
                lines[i] = 'qdrant-client==1.9.2\n'
                updated = True
                print(f"   ✓ Changed {old_version} → qdrant-client==1.9.2")
                break
        
        if updated:
            with open('requirements.txt', 'w') as f:
                f.writelines(lines)
        else:
            print("   ⚠️  qdrant-client not found in requirements.txt")
            
    except Exception as e:
        print(f"   ❌ Error updating requirements.txt: {e}")
        return 1
    
    # Step 2: Install updated package
    print("\n2️⃣ Installing qdrant-client==1.9.2...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "qdrant-client==1.9.2"], 
                      check=True, capture_output=True, text=True)
        print("   ✓ Successfully installed qdrant-client==1.9.2")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error installing: {e.stderr}")
        return 1
    
    # Step 3: Restart Qdrant container
    print("\n3️⃣ Restarting Qdrant container...")
    try:
        # Stop container
        subprocess.run(["docker-compose", "down"], check=True, capture_output=True)
        print("   ✓ Stopped Qdrant container")
        
        # Start container
        subprocess.run(["docker-compose", "up", "-d"], check=True, capture_output=True)
        print("   ✓ Started Qdrant container")
        
        # Wait for container to be ready
        print("   ⏳ Waiting for Qdrant to be ready...")
        time.sleep(5)
        
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Docker commands failed - you may need to restart manually")
        print(f"   Run: docker-compose down && docker-compose up -d")
    
    # Step 4: Test the fix
    print("\n4️⃣ Testing Qdrant connection...")
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        
        client = QdrantClient(host="localhost", port=6333)
        
        # Check if collection exists
        try:
            collections = client.get_collections()
            print(f"   ✓ Connected to Qdrant successfully")
            print(f"   ✓ Found {len(collections.collections)} collections")
            
            # Check memories collection specifically
            try:
                info = client.get_collection("memories")
                print(f"   ✓ 'memories' collection exists with {info.points_count} points")
            except:
                print("   ⚠️  'memories' collection not found - will be created on first use")
                
        except Exception as e:
            print(f"   ❌ Qdrant connection test failed: {e}")
            return 1
            
    except ImportError:
        print("   ❌ Could not import qdrant_client")
        return 1
    
    # Step 5: Quick API test
    print("\n5️⃣ Testing API health...")
    try:
        import requests
        response = requests.get("http://localhost:8000/health/detailed", timeout=5)
        health = response.json()
        
        qdrant_status = health['checks']['qdrant']['status']
        if qdrant_status == 'ok':
            print("   ✅ Qdrant health check PASSED!")
        else:
            print(f"   ⚠️  Qdrant health check status: {qdrant_status}")
            if 'error' in health['checks']['qdrant']:
                print(f"   Error: {health['checks']['qdrant']['error'][:100]}...")
                
    except Exception as e:
        print(f"   ⚠️  Could not test API health: {e}")
        print("   Make sure the API is running: make run")
    
    print("\n" + "=" * 50)
    print("✅ FIX COMPLETE!")
    print("\nNext steps:")
    print("1. Restart the API if it's running: make run")
    print("2. Test a query: curl -X POST http://localhost:8000/api/query -H 'Content-Type: application/json' -d '{\"query\": \"What is the status of Smart Analytics Dashboard?\"}'")
    print("\nIf queries still fail, check the full analysis in:")
    print("014_Hyper_Detailed_Current_State_Analysis.md")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())