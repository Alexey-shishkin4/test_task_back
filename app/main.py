from fastapi import FastAPI
from app.routers import players, games, websocket
from app.database import engine, Base


app = FastAPI()


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Battleship Game API"}
