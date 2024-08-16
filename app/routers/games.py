from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, crud, models
from app.database import SessionLocal
from typing import List


router = APIRouter(prefix="/games", tags=["games"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/create", response_model=schemas.GameResponse)
def create_game(game: schemas.GameCreate, db: Session = Depends(get_db)):
    player_1 = db.query(models.Player).filter(models.Player.id == game.player_1_id).first()
    player_2 = db.query(models.Player).filter(models.Player.id == game.player_2_id).first()

    if not player_1 or not player_2:
        raise HTTPException(status_code=400, detail="One or both players do not exist.")
    db_game = crud.create_game(db, player_1.id, player_2.id)
    return db_game


@router.get("/", response_model=List[schemas.GameResponse])
def get_active_games(db: Session = Depends(get_db)):
    return crud.get_active_games(db)
