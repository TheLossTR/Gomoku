import random
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BOARD_SIZE = 15
EMPTY = 0
PLAYER_1 = 1       # Чёрные
PLAYER_2 = 2       # Белые
BOT_PLAYER = PLAYER_2
DEFENCE_COEFF = 0.9

def check_winner(board, row, col, player):
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
    for dr, dc in directions:
        count = 1
        r, c = row + dr, col + dc
        while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and board[r][c] == player:
            count += 1
            r += dr
            c += dc
        r, c = row - dr, col - dc
        while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and board[r][c] == player:
            count += 1
            r -= dr
            c -= dc
        if count >= 5:
            return True
    return False


def is_board_full(board):
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == EMPTY:
                return False
    return True


def evaluate_window(window, player):  # Оценка одного окна из 5 клеток
    opponent = PLAYER_2 if player == PLAYER_1 else PLAYER_1
    player_count = window.count(player)
    empty_count = window.count(EMPTY)
    opponent_count = window.count(opponent)

    # Смешанные линии бесполезны
    if player_count > 0 and opponent_count > 0:
        return 0

    # Победа или поражение
    if player_count == 5:
        return 10000
    if opponent_count == 5:
        return -10000

    # Потенциальные линии
    if player_count == 4 and empty_count == 1:
        return 1000   # почти победа
    if player_count == 3 and empty_count == 2:
        return 100
    if player_count == 2 and empty_count == 3:
        return 10
    if player_count == 1 and empty_count == 4:
        return 1

    # Блокировка сильных линий противника
    if opponent_count == 4 and empty_count == 1:
        return -1000 * DEFENCE_COEFF  # нужно срочно блокировать
    if opponent_count == 3 and empty_count == 2:
        return -100 * DEFENCE_COEFF
    if opponent_count == 2 and empty_count == 3:
        return -10 * DEFENCE_COEFF

    return 0


def evaluate_board(board, player):
    score = 0
    # Горизонтали
    for r in range(BOARD_SIZE):
        row = board[r]
        for c in range(BOARD_SIZE - 4):
            window = row[c:c+5]
            score += evaluate_window(window, player)
    # Вертикали
    for c in range(BOARD_SIZE):
        col = [board[r][c] for r in range(BOARD_SIZE)]
        for r in range(BOARD_SIZE - 4):
            window = col[r:r+5]
            score += evaluate_window(window, player)
    # Диагонали (вправо-вниз)
    for r in range(BOARD_SIZE - 4):
        for c in range(BOARD_SIZE - 4):
            window = [board[r+i][c+i] for i in range(5)]
            score += evaluate_window(window, player)
    # Диагонали (влево-вниз)
    for r in range(BOARD_SIZE - 4):
        for c in range(4, BOARD_SIZE):
            window = [board[r+i][c-i] for i in range(5)]
            score += evaluate_window(window, player)
    return score


def get_bot_move(board):
    # 1. Проверяем, может ли бот немедленно выиграть
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == EMPTY:
                board[r][c] = BOT_PLAYER
                if check_winner(board, r, c, BOT_PLAYER):
                    board[r][c] = EMPTY
                    return (r, c)
                board[r][c] = EMPTY

    # 2. Блокируем победный ход противника
    opponent = PLAYER_1 if BOT_PLAYER == PLAYER_2 else PLAYER_2
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == EMPTY:
                board[r][c] = opponent
                if check_winner(board, r, c, opponent):
                    board[r][c] = EMPTY
                    return (r, c)       # обязательная блокировка
                board[r][c] = EMPTY

    # 3. Эвристический выбор
    best_score = -float('inf')
    best_move = None
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == EMPTY:
                board[r][c] = BOT_PLAYER
                score = evaluate_board(board, BOT_PLAYER)
                if score < 1000:
                    score *= random.randint(9, 11)/10
                board[r][c] = EMPTY
                if score > best_score:
                    best_score = score
                    best_move = (r, c)
    return best_move


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/move', methods=['POST'])
def make_move():
    data = request.get_json()
    board = data['board']
    row = data['row']
    col = data['col']
    player = data['player']
    game_mode = data['gameMode']

    if board[row][col] != EMPTY:
        return jsonify({'error': 'Клетка занята'}), 400

    board[row][col] = player

    winner = None
    is_draw = False
    if check_winner(board, row, col, player):
        winner = player
    elif is_board_full(board):
        is_draw = True

    bot_move = None
    if game_mode == 'bot' and not winner and not is_draw:
        bot_move = get_bot_move(board)
        if bot_move:
            br, bc = bot_move
            board[br][bc] = BOT_PLAYER
            if check_winner(board, br, bc, BOT_PLAYER):
                winner = BOT_PLAYER
            elif is_board_full(board):
                is_draw = True

    return jsonify({
        'board': board,
        'winner': winner,
        'draw': is_draw,
        'botMove': bot_move
    })


if __name__ == '__main__':
    app.run(debug=True)
