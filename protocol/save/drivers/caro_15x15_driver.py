# referee.py - Default Caro 9x9 Referee
def init_game() -> dict:
    return {
        "board": [[None for _ in range(9)] for _ in range(9)],
        "turn": 0,
        "max_turns": 81
    }

def validate_move(state: dict, move: dict, player_slot: int) -> bool:
    if not isinstance(move, dict):
        return False
    row = move.get("row")
    col = move.get("col")
    if row is None or col is None:
        return False
    if not isinstance(row, int) or not isinstance(col, int):
        return False
    if not (0 <= row < 9 and 0 <= col < 9):
        return False
    board = state.get("board", [])
    if row >= len(board) or col >= len(board[row]):
        return False
    return board[row][col] is None

def apply_move(state: dict, move: dict, player_slot: int) -> tuple:
    import copy
    new_state = copy.deepcopy(state)
    r = int(move["row"])
    c = int(move["col"])
    new_state["board"][r][c] = player_slot
    new_state["turn"] = int(new_state.get("turn", 0)) + 1
    
    board = new_state["board"]
    size = len(board)
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for dr, dc in directions:
        count = 1
        nr, nc = r + dr, c + dc
        while 0 <= nr < size and 0 <= nc < size and board[nr][nc] == player_slot:
            count += 1
            nr += dr
            nc += dc
        nr, nc = r - dr, c - dc
        while 0 <= nr < size and 0 <= nc < size and board[nr][nc] == player_slot:
            count += 1
            nr -= dr
            nc -= dc
        if count >= 5:
            return new_state, player_slot, f"Người chơi {player_slot} nối thành công 5 điểm liên tiếp!"

    if new_state["turn"] >= int(new_state.get("max_turns", 81)):
        return new_state, -1, "Hòa cờ - Đã hết lượt đi tối đa."

    return new_state, None, "Nước đi hợp lệ."
