from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from typing import List, Optional

from app.db import models as db_models
from app.models import workflow as pydantic_models

async def get_flow(db: AsyncSession, flow_id: str) -> Optional[db_models.Flow]:
    """
    Get a single flow from the database by its ID.
    """
    result = await db.execute(select(db_models.Flow).filter(db_models.Flow.id == flow_id))
    return result.scalars().first()

async def get_flows(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[db_models.Flow]:
    """
    Get all flows from the database.
    """
    result = await db.execute(select(db_models.Flow).offset(skip).limit(limit))
    return result.scalars().all()

async def create_flow(db: AsyncSession, flow: pydantic_models.Flow) -> db_models.Flow:
    """
    Create a new flow in the database from a Pydantic model.
    """
    # Convert Pydantic nested models to dictionaries for JSON storage
    nodes_dict = [node.model_dump() for node in flow.nodes]
    edges_dict = [edge.model_dump() for edge in flow.edges]

    db_flow = db_models.Flow(
        id=flow.id,
        name=flow.name,
        description=flow.description,
        nodes=nodes_dict,
        edges=edges_dict,
        created_at=flow.created_at,
        updated_at=flow.updated_at
    )
    db.add(db_flow)
    await db.commit()
    await db.refresh(db_flow)
    return db_flow

async def update_flow(db: AsyncSession, flow_id: str, flow_update_data: dict) -> Optional[db_models.Flow]:
    """
    Update an existing flow in the database.
    """
    if not flow_update_data:
        return await get_flow(db, flow_id)

    stmt = update(db_models.Flow).where(db_models.Flow.id == flow_id).values(**flow_update_data)
    result = await db.execute(stmt)
    
    if result.rowcount == 0:
        return None # Flow with the given ID was not found

    await db.commit()
    return await get_flow(db, flow_id)
