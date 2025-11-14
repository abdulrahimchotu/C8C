import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

# Pydantic Models (Schemas)
from app.models.workflow import Flow, FlowUpdate, FlowResult, NodeResult
from app.models.email import EmailSchema

# Database Layer
from app.db import crud

# Other Services
from app.services.html_service import make_request
from app.services import email_service, trigger_service

async def get_all_flows(db: AsyncSession) -> List[Flow]:
    """
    Retrieve all flows from the database.
    """
    db_flows = await crud.get_flows(db=db)
    # Convert SQLAlchemy models to Pydantic models before returning
    return [Flow.model_validate(f) for f in db_flows]

async def get_flow_by_id(db: AsyncSession, flow_id: str) -> Optional[Flow]:
    """
    Retrieve a single flow by its ID from the database.
    """
    db_flow = await crud.get_flow(db=db, flow_id=flow_id)
    if db_flow:
        return Flow.model_validate(db_flow)
    return None

async def create_new_empty_flow(db: AsyncSession) -> Flow:
    """
    Creates a new, empty flow, saves it to the DB, and returns the Pydantic model.
    """
    now = datetime.now(timezone.utc)
    new_flow_schema = Flow(
        id=str(uuid.uuid4()),
        name="New Flow",
        description="A new workflow created in the UI.",
        nodes=[],
        edges=[],
        created_at=now,
        updated_at=now,
    )
    await crud.create_flow(db=db, flow=new_flow_schema)
    return new_flow_schema

async def update_flow(db: AsyncSession, flow_id: str, flow_update: FlowUpdate) -> Optional[Flow]:
    """
    Update an existing flow in the database.
    """
    update_data = flow_update.model_dump(exclude_unset=True)
    
    # Add the updated_at timestamp
    update_data['updated_at'] = datetime.now(timezone.utc)

    db_flow = await crud.update_flow(db=db, flow_id=flow_id, flow_update_data=update_data)
    if db_flow:
        return Flow.model_validate(db_flow)
    return None

async def execute_flow(db: AsyncSession, flow_id: str) -> Optional[FlowResult]:
    """
    Executes a flow and returns a result.
    """
    flow = await get_flow_by_id(db=db, flow_id=flow_id)
    if not flow:
        return None

    # The rest of the execution logic remains the same as it operates on the Pydantic model
    start_time = datetime.now(timezone.utc)
    node_results = {}
    for node in flow.nodes:
        node_start = datetime.now(timezone.utc)
        status = "skipped"
        output_message = f"Node {node.id} of type '{node.type}' was skipped."

        if node.type == "trigger":
            if trigger_service.trigger():
                status = "succeeded"
                output_message = f"Node {node.id} of type 'trigger' executed successfully."
            else:
                status = "failed"
                output_message = f"Node {node.id} of type 'trigger' failed to execute."

        elif node.type == "http":
            config = node.config
            url = config.get("url")
            if url:
                response = await make_request(
                    method=config.get("method", "GET"),
                    url=url,
                    headers=config.get("headers"),
                    params=config.get("params"),
                    json_body=config.get("json"),
                    xml_body=config.get("xml")
                )
                status = "succeeded" if response.status_code < 400 else "failed"
                output_message = f"Node {node.id} executed. Status: {response.status_code}. Content: {response.content}"

        elif node.type == "gmail":
            config = node.config
            try:
                email_details = EmailSchema(**config)
                access_token = config.get("access_token")
                
                email_response = await email_service.send_email(
                    access_token=access_token,
                    email_data=email_details
                )
                
                if "id" in email_response:
                    status = "succeeded"
                    output_message = f"Email sent successfully. Message ID: {email_response.get('id')}"
                else:
                    status = "failed"
                    output_message = f"Failed to send email. Reason: {email_response}"

            except Exception as e:
                status = "failed"
                output_message = f"Error processing gmail node: {str(e)}"

        node_results[node.id] = NodeResult(
            node_id=node.id,
            status=status,
            output={"message": output_message},
            started_at=node_start,
            finished_at=datetime.now(timezone.utc)
        )

    return FlowResult(
        id=str(uuid.uuid4()),
        flow_id=flow_id,
        status="succeeded",
        started_at=start_time,
        finished_at=datetime.now(timezone.utc),
        results=node_results
    )
