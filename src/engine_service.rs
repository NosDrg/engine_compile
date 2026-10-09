// src/engine_service.rs
use crate::game_interface::{GameLogic, MatchResult, MoveRecord};
use crate::runner::{MatchConfig, MatchRunner};
use crate::submission_manager::{Language, SubmissionManager};
use std::path::Path;

#[derive(Debug)]
pub struct MatchOutcome {
    pub winner_id: Option<usize>,
    pub reason: String,
    pub bot0_peak_ram_mb: f64,
    pub bot1_peak_ram_mb: f64,
    pub move_history: Vec<MoveRecord>,
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

    pub fn validate_code(&self, temp_sub_id: &str, source_code: &str, lang_str: &str) -> Result<(), String> {
        let lang = Language::from_str(lang_str)?;
        let bot = self.manager.prepare_submission(temp_sub_id, source_code, lang)?;
        self.manager.cleanup(bot);
        Ok(())
    }

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

        // Chạy trận đấu
        let full_result = MatchRunner::run_match(config, &bot0, &bot1, game);

        // Dọn dẹp sandbox
        self.manager.cleanup(bot0);
        self.manager.cleanup(bot1);

        let (winner_id, reason) = match full_result.result {
            MatchResult::Win { winner, reason } => (Some(winner), reason),
            MatchResult::Draw { reason } => (None, reason),
            MatchResult::Ongoing => return Err("Lỗi trạng thái trận đấu".to_string()),
        };

        let bot0_ram_mb = (full_result.bot0_peak_ram_bytes as f64) / (1024.0 * 1024.0);
        let bot1_ram_mb = (full_result.bot1_peak_ram_bytes as f64) / (1024.0 * 1024.0);

        Ok(MatchOutcome {
            winner_id,
            reason,
            bot0_peak_ram_mb: (bot0_ram_mb * 100.0).round() / 100.0,
            bot1_peak_ram_mb: (bot1_ram_mb * 100.0).round() / 100.0,
            move_history: full_result.move_history, // Trả danh sách nước đi về
        })
    }
}