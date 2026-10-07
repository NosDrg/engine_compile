// src/runner.rs
use crate::game_interface::{GameLogic, MatchResult, Move};
use crate::process::{BotError, BotProcess};
use crate::submission_manager::PreparedBot;
use std::time::Duration;

pub struct MatchConfig {
    pub bot0_core: usize,
    pub bot1_core: usize,
    pub ram_limit_mb: u64,
    pub timeout_per_move_ms: u64,
    pub max_moves: usize,
}

pub struct MatchRunner;

impl MatchRunner {
    pub fn run_match<G: GameLogic>(
        config: MatchConfig,
        bot0_info: &PreparedBot,
        bot1_info: &PreparedBot,
        mut game: G,
    ) -> MatchResult {
        let bot0 = match BotProcess::spawn(
            0,
            &bot0_info.run_dir,
            &bot0_info.launch_cmd,
            &bot0_info.launch_args,
            config.bot0_core,
            config.ram_limit_mb,
        ) {
            Ok(b) => b,
            Err(e) => return MatchResult::Win { winner: 1, reason: format!("Không thể khởi chạy Bot 0: {}", e) },
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
            Err(e) => return MatchResult::Win { winner: 0, reason: format!("Không thể khởi chạy Bot 1: {}", e) },
        };

        let move_timeout = Duration::from_millis(config.timeout_per_move_ms);
        let mut bots = [bot0, bot1];

        for _ in 0..config.max_moves {
            let state = game.get_current_state();
            let cur_p = state.current_player;
            let other_p = 1 - cur_p;

            // 1. Serialize bàn cờ 9x9 sang JSON
            let state_json = serde_json::to_string(&state).unwrap_or_default();
            if let Err(_) = bots[cur_p].send_state(&state_json) {
                return MatchResult::Win { winner: other_p, reason: "Broken Pipe khi gửi dữ liệu".to_string() };
            }

            // 2. Đọc nước đi (I/O tối ưu qua poll)
            let (raw_move, _elapsed) = match bots[cur_p].get_move_fast(move_timeout) {
                Ok(res) => res,
                Err(BotError::Timeout(d)) => return MatchResult::Win { winner: other_p, reason: format!("Timeout (> {:.2?})", d) },
                Err(BotError::RuntimeCrash(err)) => return MatchResult::Win { winner: other_p, reason: err },
                Err(e) => return MatchResult::Win { winner: other_p, reason: format!("Lỗi I/O: {:?}", e) },
            };

            // 3. Parse nước đi
            let move_obj: Move = match serde_json::from_str(&raw_move) {
                Ok(m) => m,
                Err(_) => return MatchResult::Win { winner: other_p, reason: format!("Sai định dạng nước đi: '{}'", raw_move) },
            };

            // 4. Kiểm tra tính hợp lệ qua Logic Game
            if !game.is_legal_move(cur_p, &move_obj) {
                return MatchResult::Win { winner: other_p, reason: format!("Nước đi phạm luật: {:?}", move_obj) };
            }

            // 5. Áp dụng nước đi
            match game.apply_move(&move_obj) {
                MatchResult::Ongoing => continue,
                terminal => return terminal,
            }
        }

        MatchResult::Draw { reason: "Hết số lượt đánh tối đa".to_string() }
    }
}