from pydantic import BaseModel

class TaskCreate(BaseModel):
    description: str

class TaskResponse(BaseModel):
    id: int
    description: str