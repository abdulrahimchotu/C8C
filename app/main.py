from fastapi import FastAPI
from app.api.v1.endpoints import workflows
from app.api.v1.oauth2 import auth as oauth2_auth
from app.db import database, models

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    """
    Create database tables on application startup.
    """
    try:
        from sqlalchemy import create_engine
        sync_engine = create_engine("sqlite:///./fastapi_project.db")
        database.Base.metadata.create_all(bind=sync_engine)
    except Exception as e:
        print(f"Failed to create database tables: {e}")

app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["workflows"])
app.include_router(oauth2_auth.router, prefix="/auth/google", tags=["oauth2"])

@app.get("/")
def read_root():
    return {"Hello": "World"}