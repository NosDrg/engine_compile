// src/lib.rs
pub mod engine_service;
pub mod game_interface;
pub mod process;
pub mod runner;
pub mod submission_manager;

// Xuất các struct chính ra ngoài cho bên giao thức dễ dùng
pub use engine_service::{EngineService, MatchOutcome};
pub use game_interface::{Board9x9, GameLogic, GameStatePayload, MatchResult, Move, Piece, PieceType};