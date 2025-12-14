from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, crud, models
from ..dependencies import get_db, get_current_user

router = APIRouter()

@router.get("/", response_model=List[schemas.Invitation])
def read_invitations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """
    Retrieve invitations list. Accessible by authenticated users.
    """
    invitations = crud.get_invitations(db, skip=skip, limit=limit)
    return invitations

@router.post("/", response_model=schemas.Invitation)
def create_invitation(invitation: schemas.InvitationCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """
    Create a new invitation. Requires authentication.
    """
    return crud.create_invitation(db=db, invitation=invitation)

@router.get("/{id}", response_model=schemas.Invitation)
def read_invitation(id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """
    Fetch a single invitation by ID. Requires authentication.
    """
    db_invitation = crud.get_invitation(db, id=id)
    if db_invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return db_invitation

@router.put("/{id}", response_model=schemas.Invitation)
def update_invitation(id: int, invitation: schemas.InvitationUpdate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """
    Update an invitation by ID. Requires authentication.
    """
    db_invitation = crud.get_invitation(db, id=id)
    if db_invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return crud.update_invitation(db=db, invitation=invitation, id=id)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invitation(id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """
    Delete an invitation by ID. Requires authentication.
    """
    db_invitation = crud.get_invitation(db, id=id)
    if db_invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    crud.delete_invitation(db=db, id=id)
    return {"detail": "Invitation deleted"}