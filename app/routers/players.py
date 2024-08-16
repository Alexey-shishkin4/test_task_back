from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, crud
from app.database import SessionLocal
from typing import List


router = APIRouter(prefix="/players", tags=["players"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=schemas.PlayerResponse)
def register_player(player: schemas.PlayerCreate, db: Session = Depends(get_db)):
    db_player = crud.create_player(db, player)
    return db_player


@router.post("/login", response_model=schemas.PlayerResponse)
def login_player(player: schemas.PlayerLogin, db: Session = Depends(get_db)):
    db_player = crud.authenticate_player(db, player.username, player.password)
    if not db_player:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return db_player


@router.get("/", response_model=List[schemas.PlayerResponse])
def get_available_players(db: Session = Depends(get_db)):
    return crud.get_available_players(db)
