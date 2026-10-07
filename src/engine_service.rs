// src/engine_service.rs
use crate::game_interface::{GameLogic, MatchResult};
use crate::runner::{MatchConfig, MatchRunner};
use crate::submission_manager::{Language, SubmissionManager};
use std::path::Path;

#[derive(Debug)]
pub struct MatchOutcome {
    pub winner_id: Option<usize>,
    pub reason: String,
}

pub struct EngineService {
    manager: SubmissionManager,
}

impl EngineService {
    pub fn new(workspace_dir: &str, drivers_dir: &str) -> Self {
        Self {
            manager: SubmissionManager::new(Path::new(workspace_dir), Path::new(drivers_dir)),
        }
    }

    /// HÀM 1: Kiểm tra cú pháp khi thí sinh nộp/đổi code
    /// Giao thức truyền: ID, chuỗi code, chuỗi ngôn ngữ ("python", "cpp", "java")
    pub fn validate_code(&self, temp_sub_id: &str, source_code: &str, lang_str: &str) -> Result<(), String> {
        let lang = Language::from_str(lang_str)?;
        let bot = self.manager.prepare_submission(temp_sub_id, source_code, lang)?;
        self.manager.cleanup(bot);
        Ok(())
    }

    /// HÀM 2: Nhận thông tin 2 bot từ Database và tổ chức trận đấu
    /// Hỗ trợ cả đấu chéo ngôn ngữ (ví dụ Bot 0 viết bằng "cpp" đấu với Bot 1 viết bằng "python")
    pub fn run_duel<G: GameLogic>(
        &self,
        bot0_sub_id: &str,
        bot0_code: &str,
        bot0_lang_str: &str,
        bot1_sub_id: &str,
        bot1_code: &str,
        bot1_lang_str: &str,
        game: G,
        bot0_core: usize,
        bot1_core: usize,
    ) -> Result<MatchOutcome, String> {
        let lang0 = Language::from_str(bot0_lang_str)?;
        let lang1 = Language::from_str(bot1_lang_str)?;

        let bot0 = self.manager.prepare_submission(bot0_sub_id, bot0_code, lang0)?;
        let bot1 = self.manager.prepare_submission(bot1_sub_id, bot1_code, lang1)?;

        let config = MatchConfig {
            bot0_core,
            bot1_core,
            ram_limit_mb: 256,
            timeout_per_move_ms: 1000,
            max_moves: 100,
        };

        let result = MatchRunner::run_match(config, &bot0, &bot1, game);

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
            MatchResult::Ongoing => Err("Lỗi trạng thái trận đấu".to_string()),
        }
    }
}