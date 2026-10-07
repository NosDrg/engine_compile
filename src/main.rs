// src/main.rs
use match_runner_engine::{Board9x9, EngineService, GameLogic, GameStatePayload, MatchResult, Move, Piece, PieceType};

// Giả lập Game Logic 9x9 Kéo-Búa-Bao
struct RockPaperScissors9x9 {
    board: Board9x9,
    current_player: usize,
    round: usize,
}

impl RockPaperScissors9x9 {
    pub fn new() -> Self {
        let mut board: Board9x9 = Default::default();
        // Đặt quân Búa cho Player 0 ở (0, 0)
        board[0][0] = Some(Piece { piece_type: PieceType::Rock, owner: 0 });
        // Đặt quân Kéo cho Player 1 ở (8, 8)
        board[8][8] = Some(Piece { piece_type: PieceType::Scissors, owner: 1 });
        Self { board, current_player: 0, round: 0 }
    }
}

impl GameLogic for RockPaperScissors9x9 {
    fn get_initial_state(&self) -> GameStatePayload {
        GameStatePayload {
            board: self.board,
            current_player: self.current_player,
            time_remaining_ms: 1000,
            round: self.round,
        }
    }

    fn is_legal_move(&self, player: usize, move_obj: &Move) -> bool {
        // Tọa độ phải nằm trong bàn cờ 9x9
        if move_obj.from_x >= 9 || move_obj.from_y >= 9 || move_obj.to_x >= 9 || move_obj.to_y >= 9 {
            return false;
        }
        // Ô bắt đầu phải có quân của chính người chơi đó
        if let Some(piece) = self.board[move_obj.from_x][move_obj.from_y] {
            piece.owner == player
        } else {
            false
        }
    }

    fn apply_move(&mut self, move_obj: &Move) -> MatchResult {
        let piece = self.board[move_obj.from_x][move_obj.from_y].take();
        self.board[move_obj.to_x][move_obj.to_y] = piece;

        self.round += 1;
        self.current_player = 1 - self.current_player;

        if self.round >= 4 {
            MatchResult::Win { 
                winner: 0, 
                reason: "Hoàn tất 4 lượt đánh mẫu (Player 0 thắng)".to_string() 
            }
        } else {
            MatchResult::Ongoing
        }
    }

    fn get_current_state(&self) -> GameStatePayload {
        GameStatePayload {
            board: self.board,
            current_player: self.current_player,
            time_remaining_ms: 1000,
            round: self.round,
        }
    }
}

fn main() {
    // 1. Khởi tạo Engine Service
    // Workspace lưu bot tạm: ./workspace
    // Thư mục chứa các driver: ./drivers
    let engine = EngineService::new("./workspace", "./drivers");

    // 2. Test hàm kiểm tra cú pháp (validate_code) kèm tham số ngôn ngữ "python"
    let valid_python = "def get_move(state):\n    return {'from_x': 0, 'from_y': 0, 'to_x': 0, 'to_y': 1}";
    let invalid_python = "def get_move(state):\n    def def error_syntax!!";

    println!("--- 1. KIỂM TRA HÀM VALIDATE_CODE ---");
    match engine.validate_code("check_valid", valid_python, "python") {
        Ok(_) => println!("✔ Code hợp lệ!"),
        Err(e) => println!("✘ Lỗi cú pháp: {}", e),
    }

    match engine.validate_code("check_invalid", invalid_python, "python") {
        Ok(_) => println!("✔ Code hợp lệ!"),
        Err(e) => println!("✔ Bắt đúng lỗi cú pháp: {}", e),
    }

    // 3. Test hàm chạy trận đấu (run_duel)
    // Bot đọc vị trí quân hiện tại từ state['board'] để tránh bị báo Illegal Move
    println!("\n--- 2. KIỂM TRA HÀM RUN_DUEL ---");

    let code_bot_a = r#"
def get_move(state):
    board = state['board']
    for x in range(9):
        for y in range(9):
            piece = board[x][y]
            if piece and piece['owner'] == 0:
                return {"from_x": x, "from_y": y, "to_x": x, "to_y": (y + 1) % 9}
    return {"from_x": 0, "from_y": 0, "to_x": 0, "to_y": 0}
"#;

    let code_bot_b = r#"
def get_move(state):
    board = state['board']
    for x in range(9):
        for y in range(9):
            piece = board[x][y]
            if piece and piece['owner'] == 1:
                target_y = y - 1 if y > 0 else 8
                return {"from_x": x, "from_y": y, "to_x": x, "to_y": target_y}
    return {"from_x": 8, "from_y": 8, "to_x": 8, "to_y": 8}
"#;

    let game = RockPaperScissors9x9::new();

    // Bên giao thức truyền: ID, Code, Ngôn ngữ cho cả 2 bot, Game logic, Core ghim (0 và 1)
    match engine.run_duel(
        "sub_101", code_bot_a, "python",
        "sub_102", code_bot_b, "python",
        game,
        0, 1, // Core 0 và Core 1
    ) {
        Ok(outcome) => {
            println!("Trận đấu kết thúc!");
            println!("Người thắng: {:?}", outcome.winner_id);
            println!("Lý do: {}", outcome.reason);
        }
        Err(e) => eprintln!("Lỗi khi chạy trận: {}", e),
    }
}