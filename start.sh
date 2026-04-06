#!/bin/bash
# Start script for Render deployment

# Run database migrations if needed
# python scripts/init_db.py

# Start the application with Gunicorn
exec gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
