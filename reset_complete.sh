#!/bin/bash
# Complete reset script for Smart-Meet Lite
# Removes all data and restarts services cleanly

set -e  # Exit on error

echo "=== Smart-Meet Lite Complete Reset ==="
echo "This will:"
echo "  - Remove SQLite database"
echo "  - Stop and remove Qdrant container"
echo "  - Remove Qdrant volumes"
echo "  - Restart Qdrant fresh"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Reset cancelled."
    exit 0
fi

echo ""
echo "Step 1: Removing SQLite database and all data files..."
if [ -f "data/memories.db" ]; then
    rm -f data/memories.db
    echo "✓ SQLite database removed"
else
    echo "✓ SQLite database not found (already clean)"
fi

# Remove any backup databases
rm -f data/memories.db.backup* 2>/dev/null || true
echo "✓ Backup databases removed"

# Remove any journal files or temporary SQLite files
rm -f data/memories.db-journal 2>/dev/null || true
rm -f data/memories.db-wal 2>/dev/null || true
rm -f data/memories.db-shm 2>/dev/null || true
echo "✓ SQLite temporary files removed"

# Clear any cache directories
rm -rf __pycache__ 2>/dev/null || true
rm -rf src/__pycache__ 2>/dev/null || true
rm -rf .pytest_cache 2>/dev/null || true
echo "✓ Cache directories cleared"

# Clear any log files that might contain stale data
rm -f api_debug.log 2>/dev/null || true
rm -f *.log 2>/dev/null || true
echo "✓ Log files cleared"

echo ""
echo "Step 2: Stopping Qdrant container..."
# Stop all Qdrant containers
docker ps -a | grep qdrant | awk '{print $1}' | xargs -r docker stop 2>/dev/null || true
echo "✓ Qdrant containers stopped"

echo ""
echo "Step 3: Removing Qdrant containers..."
# Remove all Qdrant containers
docker ps -a | grep qdrant | awk '{print $1}' | xargs -r docker rm 2>/dev/null || true
echo "✓ Qdrant containers removed"

echo ""
echo "Step 4: Removing Qdrant volumes..."
# Remove specific volumes
docker volume rm smart-meet-lite_qdrant_storage 2>/dev/null || echo "  - qdrant_storage volume not found"
docker volume rm smart-meet-lite_qdrant_data 2>/dev/null || echo "  - qdrant_data volume not found"

# Remove any other Qdrant-related volumes
docker volume ls | grep qdrant | awk '{print $2}' | xargs -r docker volume rm 2>/dev/null || true
echo "✓ Qdrant volumes removed"

echo ""
echo "Step 5: Starting fresh Qdrant container..."
docker run -d \
  --name smart-meet-lite-qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v smart-meet-lite_qdrant_storage:/qdrant/storage \
  -e QDRANT__SERVICE__GRPC_PORT="6334" \
  qdrant/qdrant:v1.9.2

echo "✓ Qdrant container started"

echo ""
echo "Step 6: Waiting for Qdrant to be ready..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:6333/health > /dev/null 2>&1; then
        echo "✓ Qdrant is ready"
        break
    fi
    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        echo "✗ Qdrant failed to start properly"
        echo "Check logs with: docker logs smart-meet-lite-qdrant"
        exit 1
    fi
    echo -n "."
    sleep 1
done

echo ""
echo "Step 7: Creating fresh Qdrant collections..."
# The API will create collections on startup, but we can verify Qdrant is ready
if curl -s http://localhost:6333/collections > /dev/null 2>&1; then
    echo "✓ Qdrant API is accessible"
else
    echo "✗ Warning: Qdrant API not accessible"
fi

echo ""
echo "Step 8: Verifying services..."
docker ps | grep smart-meet-lite-qdrant > /dev/null && echo "✓ Qdrant container running" || echo "✗ Qdrant container not running"

echo ""
echo "=== Reset Complete ==="
echo "All databases and caches have been cleared and Qdrant has been restarted."
echo ""
echo "Data cleared:"
echo "  ✓ SQLite database (memories.db)"
echo "  ✓ All database backups"
echo "  ✓ SQLite temporary files (journal, wal, shm)"
echo "  ✓ Python cache directories"
echo "  ✓ Log files"
echo "  ✓ Qdrant vector data"
echo ""
echo "Next steps:"
echo "1. Start the API: make run"
echo "2. Run tests: python test_via_api.py"
echo ""