# Celery Setup for Background Jobs

## Installation

1. Install Redis (if not already installed):
```bash
# macOS
brew install redis

# Ubuntu/Debian
sudo apt-get install redis-server

# Start Redis
redis-server
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Running the System

### Terminal 1: Start Redis
```bash
redis-server
```

### Terminal 2: Start Celery Worker
```bash
./start_celery.sh
# or manually:
# celery -A app.celery_app worker --loglevel=info --concurrency=4
```

### Terminal 3: Start FastAPI
```bash
uvicorn app.main:app --reload
```

## How It Works

1. **API Request**: Client hits `/api/v1/workflows/{flow_id}/execute`
2. **Task Queue**: Celery queues the execution task
3. **Parallel Processing**: Up to 4 workers process tasks simultaneously
4. **Database Updates**: Results saved to database when complete
5. **Status Tracking**: Client polls `/executions/{execution_id}/status`

## Benefits

- **True Parallelism**: 4+ flows can execute simultaneously
- **Scalability**: Add more workers across multiple machines
- **Reliability**: Tasks persist if worker crashes
- **Monitoring**: Built-in Celery monitoring tools

## Monitoring

View active tasks:
```bash
celery -A app.celery_app inspect active
```

Monitor in real-time:
```bash
celery -A app.celery_app events
```