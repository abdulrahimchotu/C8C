from sqlalchemy import Column, String, JSON, DateTime
from app.db.database import Base

class Flow(Base):
    __tablename__ = "flows"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    nodes = Column(JSON)
    edges = Column(JSON)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class FlowExecution(Base):
    __tablename__ = "flow_executions"

    id = Column(String, primary_key=True, index=True)
    flow_id = Column(String, index=True)
    status = Column(String)  # pending, running, succeeded, failed
    started_at = Column(DateTime)
    finished_at = Column(DateTime, nullable=True)
    results = Column(JSON, nullable=True)
