from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, crud
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/reminders",
    tags=["reminders"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[schemas.Reminder])
def read_reminders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    reminders = crud.get_reminders(db, skip=skip, limit=limit, user_id=user.id)
    return reminders

@router.post("/", response_model=schemas.Reminder)
def create_reminder(reminder: schemas.ReminderCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return crud.create_user_reminder(db=db, reminder=reminder, user_id=user.id)

@router.get("/{id}", response_model=schemas.Reminder)
def read_reminder(id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    db_reminder = crud.get_reminder(db, id=id, user_id=user.id)
    if db_reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return db_reminder

@router.put("/{id}", response_model=schemas.Reminder)
def update_reminder(id: int, reminder: schemas.ReminderUpdate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    updated_reminder = crud.update_reminder(db, id=id, reminder=reminder, user_id=user.id)
    if updated_reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return updated_reminder

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    success = crud.delete_reminder(db, id=id, user_id=user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found")