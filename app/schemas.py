from pydantic import BaseModel


class PlayerCreate(BaseModel):
    username: str
    password: str


class PlayerLogin(BaseModel):
    username: str
    password: str


class PlayerResponse(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True


class GameCreate(BaseModel):
    id: int
    player_1_id: int
    player_2_id: int
    board_1: str
    board_2: str
    status: str

    class Config:
        orm_mode = True


class GameResponse(BaseModel):
    id: int
    player_1_id: int
    player_2_id: int
    player_1_board: str
    player_2_board: str
    status: str

    class Config:
        orm_mode = True


class MoveCreate(BaseModel):
    position: str


class MoveResponse(BaseModel):
    id: int
    position: str
    result: str

    class Config:
        orm_mode = True
