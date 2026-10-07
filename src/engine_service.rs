// src/engine_service.rs
use crate::game_interface::{GameLogic, MatchResult};
use crate::runner::{MatchConfig, MatchRunner};
use crate::submission_manager::SubmissionManager;
use std::path::Path;

#[derive(Debug)]
pub struct MatchOutcome {
    pub winner_id: Option<usize>, // Some(0), Some(1), hoặc None nếu hòa
    pub reason: String,
}

pub struct EngineService {
    manager: SubmissionManager,
}

impl EngineService {
    /// Khởi tạo Service (Bên giao thức chỉ cần gọi 1 lần khi server start)
    pub fn new(workspace_dir: &str, driver_path: &str) -> Self {
        Self {
            manager: SubmissionManager::new(Path::new(workspace_dir), Path::new(driver_path)),
        }
    }

    /// HÀM 1: Kiểm tra cú pháp khi thí sinh nộp/đổi code
    pub fn validate_code(&self, temp_sub_id: &str, source_code: &str) -> Result<(), String> {
        let bot = self.manager.prepare_submission(temp_sub_id, source_code)?;
        self.manager.cleanup(bot); // Kiểm tra xong dọn dẹp thư mục tạm ngay
        Ok(())
    }

    /// HÀM 2: Nhận trực tiếp chuỗi code của 2 bot từ Database và tổ chức trận đấu
    pub fn run_duel<G: GameLogic>(
        &self,
        bot0_sub_id: &str,
        bot0_code: &str,
        bot1_sub_id: &str,
        bot1_code: &str,
        game: G,
        bot0_core: usize,
        bot1_core: usize,
    ) -> Result<MatchOutcome, String> {
        // Chuẩn bị sandbox tự động cho 2 bot
        let bot0 = self.manager.prepare_submission(bot0_sub_id, bot0_code)?;
        let bot1 = self.manager.prepare_submission(bot1_sub_id, bot1_code)?;

        let config = MatchConfig {
            bot0_core,
            bot1_core,
            ram_limit_mb: 256,
            timeout_per_move_ms: 1000,
            max_moves: 100,
        };

        // Chạy trận đấu
        let result = MatchRunner::run_match(config, &bot0, &bot1, game);

        // Tự động dọn dẹp thư mục tạm của cả 2 bot sau trận
        self.manager.cleanup(bot0);
        self.manager.cleanup(bot1);

        match result {
            MatchResult::Win { winner, reason } => Ok(MatchOutcome {
                winner_id: Some(winner),
                reason,
            }),
            MatchResult::Draw { reason } => Ok(MatchOutcome {
                winner_id: None,
                reason,
            }),
            MatchResult::Ongoing => Err("Lỗi trạng thái không xác định".to_string()),
        }
    }
}