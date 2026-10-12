// src/runner.rs
use crate::game_interface::{GameLogic, MatchResult, Move, MoveRecord};
use crate::process::{BotError, BotProcess};
use crate::rps_game::RPSGame;
use crate::submission_manager::PreparedBot;
use std::time::Duration;
use crate::game_interface::Board9x9;
use serde::Serialize;

pub struct MatchConfig {
    pub bot0_core: usize,
    pub bot1_core: usize,
    pub ram_limit_mb: u64,
    pub timeout_per_move_ms: u64,
    pub max_moves: usize,
}

#[derive(Debug)]
pub struct FullMatchResult {
    pub result: MatchResult,
    pub bot0_peak_ram_bytes: u64,
    pub bot1_peak_ram_bytes: u64,
    pub move_history: Vec<MoveRecord>,
    pub initial_board: Board9x9,
}

pub struct MatchRunner;

impl MatchRunner {
    pub fn run_match<G: GameLogic>(
        config: MatchConfig,
        bot0_info: &PreparedBot,
        bot1_info: &PreparedBot,
        _game_arg: G,
    ) -> FullMatchResult {
        let mut move_history: Vec<MoveRecord> = Vec::new();

        let bot0 = match BotProcess::spawn(
            0,
            &bot0_info.run_dir,
            &bot0_info.launch_cmd,
            &bot0_info.launch_args,
            config.bot0_core,
            config.ram_limit_mb,
        ) {
            Ok(b) => b,
            Err(e) => {
                let mut dummy_game = RPSGame::new();
                return FullMatchResult {
                    result: MatchResult::Win {
                        winner: 1,
                        reason: format!("Không thể khởi chạy Bot 0: {}", e),
                    },
                    bot0_peak_ram_bytes: 0,
                    bot1_peak_ram_bytes: 0,
                    move_history,
                    initial_board: dummy_game.get_initial_state().board,
                };
            }
        };

        let bot1 = match BotProcess::spawn(
            1,
            &bot1_info.run_dir,
            &bot1_info.launch_cmd,
            &bot1_info.launch_args,
            config.bot1_core,
            config.ram_limit_mb,
        ) {
            Ok(b) => b,
            Err(e) => {
                let mut dummy_game = RPSGame::new();
                return FullMatchResult {
                    result: MatchResult::Win {
                        winner: 0,
                        reason: format!("Không thể khởi chạy Bot 1: {}", e),
                    },
                    bot0_peak_ram_bytes: bot0.peak_ram_bytes,
                    bot1_peak_ram_bytes: 0,
                    move_history,
                    initial_board: dummy_game.get_initial_state().board,
                };
            }
        };

        let move_timeout = Duration::from_millis(config.timeout_per_move_ms);
        let mut bots = [bot0, bot1];
        let mut final_result = MatchResult::Draw {
            reason: "Hết số lượt đánh tối đa".to_string(),
        };

        let mut game = RPSGame::new();
        // Lấy bàn cờ chuẩn do Rust Engine khởi tạo
        let initial_board = game.get_initial_state().board;
        let mut current_state = game.get_initial_state();

        for current_round in 0..config.max_moves {
            let cur_p = current_state.current_player;
            let other_p = 1 - cur_p;

            let state_json = serde_json::to_string(&current_state).unwrap_or_default();
            if let Err(_) = bots[cur_p].send_state(&state_json) {
                final_result = MatchResult::Win {
                    winner: other_p,
                    reason: "Broken Pipe khi gửi dữ liệu".to_string(),
                };
                break;
            }

            let (raw_move_str, elapsed) = match bots[cur_p].get_move_fast(move_timeout) {
                Ok((mv, res)) => (mv.to_string(), res),
                Err(BotError::Timeout(d)) => {
                    final_result = MatchResult::Win {
                        winner: other_p,
                        reason: format!("Timeout (> {:.2?})", d),
                    };
                    break;
                }
                Err(BotError::RuntimeCrash(err)) => {
                    final_result = MatchResult::Win {
                        winner: other_p,
                        reason: err,
                    };
                    break;
                }
                Err(e) => {
                    final_result = MatchResult::Win {
                        winner: other_p,
                        reason: format!("Lỗi I/O: {:?}", e),
                    };
                    break;
                }
            };

            bots[cur_p].update_peak_memory();

            let move_obj: Move = match serde_json::from_str(&raw_move_str) {
                Ok(m) => m,
                Err(_) => {
                    final_result = MatchResult::Win {
                        winner: other_p,
                        reason: format!("Sai định dạng nước đi: '{}'", raw_move_str),
                    };
                    break;
                }
            };

            if !game.is_legal_move(cur_p, &move_obj) {
                final_result = MatchResult::Win {
                    winner: other_p,
                    reason: format!("Nước đi phạm luật: {:?}", move_obj),
                };
                break;
            }

            move_history.push(MoveRecord {
                round: current_round,
                player: cur_p,
                move_obj: move_obj.clone(),
                elapsed_ms: elapsed.as_millis(),
            });

            match game.apply_move(&move_obj) {
                MatchResult::Ongoing => {
                    current_state = game.get_current_state();
                    continue;
                }
                terminal => {
                    final_result = terminal;
                    break;
                }
            }
        }

        let [mut b0, mut b1] = bots;
        b0.update_peak_memory();
        b1.update_peak_memory();

        FullMatchResult {
            result: final_result,
            bot0_peak_ram_bytes: b0.peak_ram_bytes,
            bot1_peak_ram_bytes: b1.peak_ram_bytes,
            move_history,
            initial_board,
        }
    }
}