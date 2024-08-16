from sqlalchemy.orm import Session
from app import models, schemas
from passlib.context import CryptContext
from typing import List
import random
import bcrypt


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_player(db: Session, player: schemas.PlayerCreate):
    hashed_password = get_password_hash(player.password)
    db_player = models.Player(username=player.username, password_hash=hashed_password)
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player


def authenticate_player(db: Session, username: str, password: str):
    """
    Аутентификация игрока по имени пользователя и паролю.
    Возвращает объект игрока, если аутентификация успешна, иначе None.
    """
    player = db.query(models.Player).filter(models.Player.username == username).first()

    if player is None:
        return None

    if not bcrypt.checkpw(password.encode('utf-8'), player.hashed_password.encode('utf-8')):
        return None

    return player


def get_available_players(db: Session):
    """
    Возвращает список игроков, которые доступны для игры (не участвуют в активных играх).
    """
    # Подзапрос для получения всех игроков, которые заняты (участвуют в активных играх)
    busy_players = db.query(models.Game.player_1_id).filter(models.Game.status == "active").union(
        db.query(models.Game.player_2_id).filter(models.Game.status == "active")).subquery()

    # Запрос для получения всех игроков, которые не заняты
    available_players = db.query(models.Player).filter(~models.Player.id.in_(busy_players)).all()

    return available_players


def create_game(db: Session, player_1_id: int, player_2_id: int):
    """
    Создает новую игру между двумя игроками.
    Генерирует случайные доски для каждого игрока и сохраняет игру в базе данных.
    Возвращает объект игры.
    """
    # Генерация досок для обоих игроков
    player_1_board = generate_random_board()
    player_2_board = generate_random_board()

    # Создание объекта новой игры
    new_game = models.Game(
        player_1_id=player_1_id,
        player_2_id=player_2_id,
        player_1_board=player_1_board,
        player_2_board=player_2_board,
        status="active"  # Изначально статус игры активен
    )

    # Добавление игры в сессию и сохранение в базе данных
    db.add(new_game)
    db.commit()
    db.refresh(new_game)  # Обновляем объект new_game, чтобы получить его id и другие атрибуты

    return new_game


def get_active_games(db: Session):
    return db.query(models.Game).filter(models.Game.status == "active").all()


def generate_random_board(size: int = 10) -> str:
    board = [["~"] * size for _ in range(size)]
    ships = {
        "4": 1,  # 1 корабль размером 4 клетки
        "3": 2,  # 2 корабля размером 3 клетки
        "2": 3,  # 3 корабля размером 2 клетки
        "1": 4  # 4 корабля размером 1 клетка
    }

    def is_valid_position(board, x, y, length, orientation):
        """Проверка, можно ли разместить корабль на доске"""
        dx, dy = (1, 0) if orientation == 'horizontal' else (0, 1)

        for i in range(length):
            nx, ny = x + i * dx, y + i * dy
            if nx >= size or ny >= size or board[ny][nx] != "~":
                return False

            # Проверяем соседние клетки, чтобы корабли не касались
            for ix in range(-1, 2):
                for iy in range(-1, 2):
                    cx, cy = nx + ix, ny + iy
                    if 0 <= cx < size and 0 <= cy < size and board[cy][cx] != "~":
                        return False
        return True

    def place_ship(board, x, y, length, orientation):
        """Размещение корабля на доске"""
        dx, dy = (1, 0) if orientation == 'horizontal' else (0, 1)
        for i in range(length):
            nx, ny = x + i * dx, y + i * dy
            board[ny][nx] = "O"

    for length, count in ships.items():
        length = int(length)
        for _ in range(count):
            while True:
                x, y = random.randint(0, size - 1), random.randint(0, size - 1)
                orientation = random.choice(['horizontal', 'vertical'])
                if is_valid_position(board, x, y, length, orientation):
                    place_ship(board, x, y, length, orientation)
                    break

    # Преобразуем доску в строку для сохранения в базе данных
    return "\n".join(["".join(row) for row in board])


def get_activate_games(db: Session):
    return db.query(models.Game).filter(models.Game.status == "active").all()


def create_move(db: Session, move: schemas.MoveCreate, game_id: int, player_id: int):
    result = evaluate_move(move.position)  # Проверка результата хода
    db_move = models.Move(
        game_id=game_id,
        player_id=player_id,
        position=move.position,
        result=result
    )
    db.add(db_move)
    db.commit()
    db.refresh(db_move)
    return db_move


def evaluate_move(board: List[List[str]], position: str) -> str:
    # Преобразование позиции из строки в индексы
    x = ord(position[0].upper()) - ord('A')
    y = int(position[1:]) - 1

    if board[y][x] == "~":
        # Промах
        board[y][x] = "M"  # Обозначаем промах на доске
        return "miss"
    elif board[y][x] == "O":
        # Попадание
        board[y][x] = "X"  # Обозначаем попадание на доске

        # Проверяем, потоплен ли корабль
        if is_ship_sunk(board, x, y):
            return "sink"
        else:
            return "hit"
    elif board[y][x] in ["M", "X"]:
        # Если клетка уже была атакована ранее
        raise ValueError("Position already attacked")


def is_ship_sunk(board: List[List[str]], x: int, y: int) -> bool:
    """Проверяем, потоплен ли корабль, к которому принадлежит пораженная часть"""

    def check_direction(dx: int, dy: int) -> bool:
        nx, ny = x + dx, y + dy
        while 0 <= nx < len(board) and 0 <= ny < len(board):
            if board[ny][nx] == "O":
                return False  # Если есть непораженная часть корабля, корабль не потоплен
            if board[ny][nx] == "~" or board[ny][nx] == "M":
                break  # Достигли конца корабля или воды
            nx, ny = nx + dx, ny + dy
        return True

    # Проверяем в четырех направлениях (влево, вправо, вверх, вниз)
    return (check_direction(1, 0) and  # вправо
            check_direction(-1, 0) and  # влево
            check_direction(0, 1) and  # вниз
            check_direction(0, -1))  # вверх
