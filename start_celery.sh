#!/bin/bash
# Start Celery worker
cd /Users/consultadd/Downloads/langflow-backend/fastapi_project
celery -A app.celery_app worker --loglevel=info --concurrency=4