from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Flow, FlowUpdate, FlowResult
from app.services import workflow_service
from app.db.database import AsyncSessionLocal

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

@router.post("/{flow_id}/execute", response_model=FlowResult)
async def execute_existing_flow(flow_id: str, db: AsyncSession = Depends(get_db)):
    """
    Execute a flow and get the results.
    """
    result = await workflow_service.execute_flow(db=db, flow_id=flow_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    return result