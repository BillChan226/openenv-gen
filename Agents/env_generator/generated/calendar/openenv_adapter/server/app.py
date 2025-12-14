from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from calendar_environment import CalendarEnvironment

app = FastAPI()
environment = CalendarEnvironment()

class ResetModel(BaseModel):
    seed: Optional[int] = None

class StepModel(BaseModel):
    action: str
    data: dict

class StateModel(BaseModel):
    users: List[dict]
    events: List[dict]
    invitations: List[dict]
    reminders: List[dict]

@app.post("/reset")
async def reset_environment(reset_model: ResetModel):
    try:
        environment.reset(seed=reset_model.seed)
        return {"message": "Environment reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/step")
async def perform_step(step_model: StepModel):
    try:
        result = environment.step(action=step_model.action, data=step_model.data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/state", response_model=StateModel)
async def get_state():
    try:
        state = environment.state()
        return state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    try:
        # Placeholder for actual health check logic
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))