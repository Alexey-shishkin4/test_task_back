from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from typing import List, Dict
from app.database import SessionLocal
from app import crud, models, schemas


router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}  # game_id -> list of connections

    async def connect(self, websocket: WebSocket, game_id: int):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
        self.active_connections[game_id].append(websocket)

    def disconnect(self, websocket: WebSocket, game_id: int):
        self.active_connections[game_id].remove(websocket)
        if not self.active_connections[game_id]:
            del self.active_connections[game_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, game_id: int):
        for connection in self.active_connections.get(game_id, []):
            await connection.send_text(message)


manager = ConnectionManager()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.websocket("/games/{game_id}/play")
async def websocket_endpoint(websocket: WebSocket, game_id: int, db: Session = Depends(get_db)):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()

    if not game:
        await websocket.close(code=1000)
        return

    await manager.connect(websocket, game_id)

    try:
        while True:
            data = await websocket.receive_text()
            move_data = schemas.MoveCreate(position=data)
            player_id = int(websocket.headers.get('player_id'))

            # Проверка, является ли пользователь частью этой игры
            if player_id not in [game.player_1_id, game.player_2_id]:
                await manager.send_personal_message("You are not part of this game.", websocket)
                continue

            # создание нового хода
            move = crud.create_move(db=db, move=move_data, game_id=game_id, player_id=player_id)

            # Отправка результата всем участникам
            await manager.broadcast(f"Player {player_id} moved to {move.position} with result {move.result}", game_id)

            # Проверка на завершение игры
            if move.result == "sink" and check_if_game_over(db, game_id, player_id):
                game.status = "finished"
                game.winner_id = player_id
                db.commit()

                await manager.broadcast(f"Game over! Player {player_id} wins!", game_id)
                break
    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)
        await manager.broadcast(f"Player disconnected", game_id)


def check_if_game_over(db: Session, game_id: int, player_id: int) -> bool:
    # Логика проверки, закончены ли все корабли у другого игрока
    # Если все корабли потоплены, игра закончена
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if player_id == game.player_1_id:
        # Проверка доски игрока 2
        opponent_board = game.board_2
    else:
        # Проверка доски игрока 1
        opponent_board = game.board_1

    # Примерная проверка, нужно учитывать все корабли
    return "sink" not in opponent_board  # Заглушка, здесь будет реальная проверка
