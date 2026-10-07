// src/game_interface.rs
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PieceType {
    Rock,     // Búa
    Paper,    // Bao
    Scissors, // Kéo
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Piece {
    pub piece_type: PieceType,
    pub owner: usize, // 0 hoặc 1
}

pub type Board9x9 = [[Option<Piece>; 9]; 9];

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Move {
    pub from_x: usize,
    pub from_y: usize,
    pub to_x: usize,
    pub to_y: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GameStatePayload {
    pub board: Board9x9,
    pub current_player: usize,
    pub time_remaining_ms: u64,
    pub round: usize,
}

#[derive(Debug, PartialEq, Eq, Clone, Serialize, Deserialize)]
pub enum MatchResult {
    Win { winner: usize, reason: String },
    Draw { reason: String },
    Ongoing,
}

pub trait GameLogic {
    fn get_initial_state(&self) -> GameStatePayload;
    fn is_legal_move(&self, player: usize, move_obj: &Move) -> bool;
    fn apply_move(&mut self, move_obj: &Move) -> MatchResult;
    fn get_current_state(&self) -> GameStatePayload;
}