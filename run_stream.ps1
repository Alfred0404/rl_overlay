# Start the overlay server in TEST MODE with mock data from data/test_event.json
# Usage: .\run_stream.ps1

$env:TEST_MODE = "false"
python -m uvicorn src.server:app --reload --host 0.0.0.0 --port 8000
