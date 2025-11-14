from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# The database URL points to a local file named fastapi_project.db
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./fastapi_project.db"

# The engine is the entry point to the database.
# connect_args is needed only for SQLite.
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Each instance of AsyncSessionLocal will be a database session.
AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our SQLAlchemy models to inherit from.
Base = declarative_base()
