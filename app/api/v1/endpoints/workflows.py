from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Flow, FlowUpdate, FlowResult, ExecutionStatus, NodeResult
from app.services import workflow_service
from app.db.database import AsyncSessionLocal
from app.db import crud
import uuid
from datetime import datetime, timezone

router = APIRouter()

# Dependency to get a DB session for each request
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

@router.post("/new", response_model=Flow, status_code=status.HTTP_201_CREATED)
async def create_new_empty_flow(db: AsyncSession = Depends(get_db)):
    """
    Create a new, empty workflow and return it.
    """
    return await workflow_service.create_new_empty_flow(db=db)

@router.get("/", response_model=List[Flow])
async def read_all_flows(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all flows.
    """
    return await workflow_service.get_all_flows(db=db)

@router.get("/{flow_id}", response_model=Flow)
async def read_single_flow(flow_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a single flow by its ID.
    """
    flow = await workflow_service.get_flow_by_id(db=db, flow_id=flow_id)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    return flow

@router.put("/{flow_id}", response_model=Flow)
async def update_existing_flow(flow_id: str, flow_in: FlowUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an existing flow (used for saving).
    """
    updated_flow = await workflow_service.update_flow(db=db, flow_id=flow_id, flow_update=flow_in)
    if not updated_flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    return updated_flow

@router.post("/{flow_id}/execute", response_model=ExecutionStatus)
async def execute_existing_flow(flow_id: str, db: AsyncSession = Depends(get_db)):
    """
    Execute a flow in background and return execution ID for tracking.
    """
    # Check if flow exists
    flow = await workflow_service.get_flow_by_id(db=db, flow_id=flow_id)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    
    # Create execution record
    execution_id = str(uuid.uuid4())
    execution_result = FlowResult(
        id=execution_id,
        flow_id=flow_id,
        status="pending",
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        results={}
    )
    
    await crud.create_flow_execution(db, execution_result)
    
    # Start Celery task
    from app.celery_app import execute_flow_task
    execute_flow_task.delay(flow_id, execution_id)
    
    return ExecutionStatus(
        execution_id=execution_id,
        flow_id=flow_id,
        status="pending",
        message="Flow execution started in background"
    )

@router.get("/executions/{execution_id}", response_model=FlowResult)
async def get_execution_result(execution_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get execution status and results by execution ID.
    """
    execution = await crud.get_flow_execution(db, execution_id)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    
    # Convert database model back to Pydantic model
    results = {}
    if execution.results and isinstance(execution.results, dict):
        for node_id, result_data in execution.results.items():
            if isinstance(result_data, dict):
                # Convert datetime strings back to datetime objects
                if 'started_at' in result_data and isinstance(result_data['started_at'], str):
                    result_data['started_at'] = datetime.fromisoformat(result_data['started_at'].replace('Z', '+00:00'))
                if 'finished_at' in result_data and isinstance(result_data['finished_at'], str):
                    result_data['finished_at'] = datetime.fromisoformat(result_data['finished_at'].replace('Z', '+00:00'))
                
                results[node_id] = NodeResult(**result_data)
    
    return FlowResult(
        id=execution.id,
        flow_id=execution.flow_id,
        status=execution.status,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        results=results
    )

@router.get("/executions/{execution_id}/status")
async def get_execution_status(execution_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get just the execution status (lightweight endpoint).
    """
    execution = await crud.get_flow_execution(db, execution_id)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    
    return {
        "execution_id": execution.id,
        "flow_id": execution.flow_id,
        "status": execution.status,
        "started_at": execution.started_at,
        "finished_at": execution.finished_at
    }