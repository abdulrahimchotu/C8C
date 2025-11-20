from celery import Celery
import asyncio
from app.services.workflow_service import execute_flow_background

# Celery configuration
celery_app = Celery(
    "workflow_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@celery_app.task
def execute_flow_task(flow_id: str, execution_id: str):
    """Celery task for flow execution."""
    return asyncio.run(execute_flow_background(flow_id, execution_id))