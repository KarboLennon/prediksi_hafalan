#!/bin/bash
# Start script for Railway deployment

# Railway auto-injects PORT variable
# Start the application with Gunicorn + Uvicorn workers
exec gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000}

