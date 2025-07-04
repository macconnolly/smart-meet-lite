#!/bin/bash
# Start API with logging to file

echo "Starting API with logging to api_debug.log..."
source venv/bin/activate
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --log-level info 2>&1 | tee api_debug.log