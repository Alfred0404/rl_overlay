#!/bin/bash
# Start the overlay server in TEST MODE with mock data from data/test_event.json
# Usage: ./run_test.sh

TEST_MODE=true python -m uvicorn src.server:app --reload --host 0.0.0.0 --port 8000
