import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

# Pydantic Models (Schemas)
from app.models.workflow import Flow, FlowUpdate, FlowResult, NodeResult,Node
from app.models.email import EmailSchema

# Database Layer
from app.db import crud

# Other Services
from app.services.html_service import make_request
from app.services import email_service, trigger_service,slack_service

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

def _topological_sort(nodes: List[Node]) -> List[Node]:
    """
    Perform topological sort on nodes based on dependencies.
    """
    node_map = {node.id: node for node in nodes}
    visited = set()
    temp_visited = set()
    result = []
    
    def visit(node_id: str):
        if node_id in temp_visited:
            raise ValueError(f"Circular dependency detected involving node {node_id}")
        if node_id in visited:
            return
            
        temp_visited.add(node_id)
        node = node_map.get(node_id)
        if node:
            for dep_id in node.dependencies:
                visit(dep_id)
        temp_visited.remove(node_id)
        visited.add(node_id)
        if node:
            result.append(node)
    
    for node in nodes:
        if node.id not in visited:
            visit(node.id)
    
    return result

async def _execute_node(node, flow_outputs: Dict[str, Any]) -> NodeResult:
    """
    Execute a single node and return its result.
    """
    node_start = datetime.now(timezone.utc)
    status = "skipped"
    output = {}
    
    try:
        if node.type == "trigger":
            if trigger_service.trigger():
                status = "succeeded"
                output = {"message": "Trigger executed successfully", "triggered": True}
            else:
                status = "failed"
                output = {"message": "Trigger failed", "triggered": False}
                
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
                output = {
                    "status_code": response.status_code,
                    "content": response.content
                }
            else:
                status = "failed"
                output = {"error": "No URL provided"}
                
        elif node.type == "slack":
            config = node.config
            message_text = flow_outputs.get('http-1', {}).get('content', "empty text received")
            token = config.get("token")
            channel_id = "C09SENRHMDG"

            if not token or not channel_id or not message_text:
                status = "failed"
                output = {"error": "Slack token, channel ID, or message text is missing"}
            else:
                slack_response = await slack_service.send_slack_message(token, channel_id, message_text)
                if slack_response.get("ok"):
                    status = "succeeded"
                    output = {"message_id": slack_response.get("ts"), "sent": True}
                else:
                    status = "failed"
                    output = {"error": slack_response.get("error"), "sent": False}
                
        elif node.type == "gmail":
            config = node.config
            config['body']=str(flow_outputs.get('http-1', {}).get('content', "empty text received"))
            email_details = EmailSchema(**config)
            access_token = config.get("access_token")
            
            email_response = await email_service.send_email(
                access_token=access_token,
                email_data=email_details
            )
            
            if "id" in email_response:
                status = "succeeded"
                output = {"message_id": email_response.get("id"), "sent": True}
            else:
                status = "failed"
                output = {"error": email_response, "sent": False}
                
    except Exception as e:
        status = "failed"
        output = {"error": str(e)}
    
    return NodeResult(
        node_id=node.id,
        status=status,
        output=output,
        started_at=node_start,
        finished_at=datetime.now(timezone.utc)
    )

async def execute_flow_background(flow_id: str, execution_id: str) -> None:
    """
    Background task to execute flow and save results to database.
    """
    from app.db.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            # Update status to running
            await crud.update_flow_execution(db, execution_id, "running")
            
            # Execute the flow
            result = await execute_flow(db, flow_id)
            if result:
                # Save results to database
                results_dict = {k: v.model_dump() for k, v in result.results.items()}
                await crud.update_flow_execution(
                    db, execution_id, result.status, result.finished_at, results_dict
                )
        except Exception as e:
            # Handle any errors during execution
            await crud.update_flow_execution(
                db, execution_id, "failed", datetime.now(timezone.utc), 
                {"error": str(e)}
            )

async def execute_flow(db: AsyncSession, flow_id: str) -> Optional[FlowResult]:
    """
    Executes a flow using topological sort for proper dependency order.
    """
    flow = await get_flow_by_id(db=db, flow_id=flow_id)
    if not flow:
        return None

    start_time = datetime.now(timezone.utc)
    flow_outputs = {}  # Store outputs from all nodes
    node_results = {}
    
    try:
        # Sort nodes by dependencies
        sorted_nodes = _topological_sort(flow.nodes)
        print([node.id for node in sorted_nodes])

        for node in sorted_nodes:
            result = await _execute_node(node, flow_outputs)
            node_results[node.id] = result
            flow_outputs[node.id] = result.output
            # print(flow_outputs)
            
            # Stop execution if a node fails
            if result.status == "failed":
                break
                
        overall_status = "succeeded" if all(r.status == "succeeded" for r in node_results.values()) else "failed"
        
    except ValueError as e:
        # Handle circular dependency
        overall_status = "failed"
        node_results = {"error": NodeResult(
            node_id="system",
            status="failed",
            output={"error": str(e)},
            started_at=start_time,
            finished_at=datetime.now(timezone.utc)
        )}

    return FlowResult(
        id=str(uuid.uuid4()),
        flow_id=flow_id,
        status=overall_status,
        started_at=start_time,
        finished_at=datetime.now(timezone.utc),
        results=node_results
    )
