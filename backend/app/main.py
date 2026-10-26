
from fastapi import FastAPI

app = FastAPI(
    title="Queue Management System",
    description="Rule-based queue monitoring and customer counting",
    version="0.1.0",
)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "application": "Queue Management System",
    }
