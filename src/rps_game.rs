// src/rps_game.rs
use crate::game_interface::{
    Board9x9, GameLogic, GameStatePayload, MatchResult, Move, Piece, PieceType, BOARD_SIZE,
};
use rand::seq::SliceRandom;

#[derive(Clone)]
pub struct RPSGame {
    board: Board9x9,
    current_player: usize,
    round: usize,
    time_ms: u64,
}

impl RPSGame {
    pub fn new() -> Self {
        let mut game = Self {
            board: [[None; BOARD_SIZE]; BOARD_SIZE],
            current_player: 0,
            round: 0,
            time_ms: 1000,
        };
        game.setup_board();
        game
    }

    fn setup_board(&mut self) {
        // Dùng rand::rng() tương thích chuẩn rand 0.9
        let mut rng = rand::rng();
        let mut positions = Vec::new();

        for y in 0..4 {
            for x in 0..BOARD_SIZE {
                if (x == 0 && y == 0) || (x == 8 && y == 8) {
                    continue;
                }
                positions.push((x, y));
            }
        }
        positions.shuffle(&mut rng);

        let mut pieces = vec![
            PieceType::Rock, PieceType::Rock, PieceType::Rock,
            PieceType::Paper, PieceType::Paper, PieceType::Paper,
            PieceType::Scissors, PieceType::Scissors, PieceType::Scissors,
        ];
        pieces.shuffle(&mut rng);

        for i in 0..9 {
            let (x, y) = positions[i];
            let mirror_x = BOARD_SIZE - 1 - x;
            let mirror_y = BOARD_SIZE - 1 - y;

            self.board[y][x] = Some(Piece { piece_type: pieces[i], owner: 0 });
            self.board[mirror_y][mirror_x] = Some(Piece { piece_type: pieces[i], owner: 1 });
        }
    }

    fn can_capture(attacker: PieceType, defender: PieceType) -> bool {
        matches!(
            (attacker, defender),
            (PieceType::Rock, PieceType::Scissors)
                | (PieceType::Scissors, PieceType::Paper)
                | (PieceType::Paper, PieceType::Rock)
        )
    }

    fn check_win(&self, player: usize) -> Option<String> {
        let (tx, ty) = if player == 0 { (8, 8) } else { (0, 0) };
        if let Some(p) = self.board[ty][tx] {
            if p.owner == player {
                return Some(if player == 0 { "REACH_I9".to_string() } else { "REACH_A1".to_string() });
            }
        }

        let opponent = 1 - player;
        let mut has_rock = false;
        let mut has_paper = false;
        let mut has_scissors = false;

        for row in &self.board {
            for cell in row {
                if let Some(p) = cell {
                    if p.owner == opponent {
                        match p.piece_type {
                            PieceType::Rock => has_rock = true,
                            PieceType::Paper => has_paper = true,
                            PieceType::Scissors => has_scissors = true,
                        }
                    }
                }
            }
        }

        if !has_rock { return Some("ELIMINATED_ROCK".to_string()); }
        if !has_paper { return Some("ELIMINATED_PAPER".to_string()); }
        if !has_scissors { return Some("ELIMINATED_SCISSORS".to_string()); }

        None
    }
}

impl GameLogic for RPSGame {
    fn get_initial_state(&mut self) -> GameStatePayload {
        self.get_current_state()
    }

    fn is_legal_move(&self, player: usize, m: &Move) -> bool {
        if player != 0 && player != 1 { return false; }
        if m.from_x >= BOARD_SIZE || m.from_y >= BOARD_SIZE || m.to_x >= BOARD_SIZE || m.to_y >= BOARD_SIZE {
            return false;
        }
        if m.from_x == m.to_x && m.from_y == m.to_y { return false; }

        let src = match self.board[m.from_y][m.from_x] {
            Some(p) if p.owner == player => p,
            _ => return false,
        };

        let dx = (m.to_x as isize) - (m.from_x as isize);
        let dy = (m.to_y as isize) - (m.from_y as isize);
        if dx < -1 || dx > 1 || dy < -1 || dy > 1 { return false; }

        match self.board[m.to_y][m.to_x] {
            None => true,
            Some(dst) => {
                if dst.owner == player || dst.piece_type == src.piece_type {
                    false
                } else {
                    Self::can_capture(src.piece_type, dst.piece_type)
                }
            }
        }
    }

    fn apply_move(&mut self, m: &Move) -> MatchResult {
        if !self.is_legal_move(self.current_player, m) {
            return MatchResult::Win {
                winner: 1 - self.current_player,
                reason: "INVALID_MOVE".to_string(),
            };
        }

        let moving = self.board[m.from_y][m.from_x].take();
        self.board[m.to_y][m.to_x] = moving;
        self.round += 1;

        if let Some(reason) = self.check_win(self.current_player) {
            return MatchResult::Win {
                winner: self.current_player,
                reason,
            };
        }

        self.current_player = 1 - self.current_player;
        MatchResult::Ongoing
    }

    fn get_current_state(&self) -> GameStatePayload {
        GameStatePayload {
            board: self.board,
            current_player: self.current_player,
            round: self.round,
            time_remaining_ms: self.time_ms,
        }
    }
}