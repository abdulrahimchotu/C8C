from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime


class Edge(BaseModel):
    id: str
    source: str
    target: str
    condition: Optional[Dict[str, Any]] = None


class Position(BaseModel):
    x: float
    y: float

class Node(BaseModel):
    id: str
    type: str
    position: Position
    config: Dict[str, Any] = {}
    dependents: List[str] = []
    dependencies: List[str] = []


class Flow(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    description: Optional[str] = None
    nodes: list[Node]
    edges: list[Edge]
    created_at: datetime
    updated_at: datetime

class NodeResult(BaseModel):
    node_id: str
    status: str
    output: Dict[str, Any] = {}
    error: Optional[str] = None
    started_at: datetime
    finished_at: datetime


class FlowResult(BaseModel):
    id: str
    flow_id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    results: Dict[str, NodeResult]  # node_id -> result

class ExecutionStatus(BaseModel):
    execution_id: str
    flow_id: str
    status: str
    message: str

# Schema for creating a new flow
class FlowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    nodes: list[Node]
    edges: list[Edge]

# Schema for updating an existing flow
class FlowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[list[Node]] = None
    edges: Optional[list[Edge]] = None