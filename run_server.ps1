$ErrorActionPreference = "Stop"

# Four in a Square backend server (FastAPI)
# Runs on all interfaces so emulators/devices can connect.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

