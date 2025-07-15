from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.models import TaskCreate, TaskResponse
from app.database import engine, Base, SessionLocal
from app.schema import Task

app = FastAPI()

# Create the database tables
Base.metadata.create_all(bind=engine)

@app.post("/run-task", response_model=TaskResponse)
def run_task(task: TaskCreate):
    db = SessionLocal()
    db_task = Task(description=task.description)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    db.close()
    return TaskResponse(id=db_task.id, description=db_task.description)