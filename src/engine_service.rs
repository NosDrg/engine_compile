// src/engine_service.rs
use crate::game_interface::{GameLogic, MoveRecord};
use crate::runner::{MatchConfig, MatchRunner};
use crate::submission_manager::{Language, SubmissionManager};
use serde::Serialize;
use std::path::Path;

#[derive(Debug, Serialize)]
pub struct MatchOutcome {
    pub winner_id: Option<usize>,
    pub reason: String,
    pub bot0_peak_ram_mb: f64,
    pub bot1_peak_ram_mb: f64,
    pub move_history: Vec<MoveRecord>,
    pub initial_board: crate::game_interface::Board9x9,
}

pub struct EngineService {
    pub manager: SubmissionManager,
}

impl EngineService {
    pub fn new(workspace_dir: &str, drivers_dir: &str) -> Self {
        Self {
            manager: SubmissionManager::new(Path::new(workspace_dir), Path::new(drivers_dir)),
        }
    }

    fn parse_language(lang_str: &str) -> Result<Language, String> {
        match lang_str.to_lowercase().as_str() {
            "python" | "py" => Ok(Language::Python),
            "cpp" | "c++" => Ok(Language::Cpp),
            "java" => Ok(Language::Java),
            other => Err(format!("Ngôn ngữ không được hỗ trợ: {}", other)),
        }
    }

    pub fn validate_code(&self, temp_sub_id: &str, source_code: &str, lang: &str) -> Result<(), String> {
        let language = Self::parse_language(lang)?;
        let bot = self.manager.prepare_submission(temp_sub_id, source_code, language)?;
        self.manager.cleanup(bot);
        Ok(())
    }

    pub fn run_duel<G: GameLogic>(
        &self,
        bot0_id: &str,
        bot0_code: &str,
        bot0_lang: &str,
        bot1_id: &str,
        bot1_code: &str,
        bot1_lang: &str,
        mut game: G,
        bot0_core: usize,
        bot1_core: usize,
    ) -> Result<MatchOutcome, String> {
        let lang0 = Self::parse_language(bot0_lang)?;
        let lang1 = Self::parse_language(bot1_lang)?;

        let prep0_res = self.manager.prepare_submission(bot0_id, bot0_code, lang0);
        let prep1_res = self.manager.prepare_submission(bot1_id, bot1_code, lang1);

        if prep0_res.is_err() && prep1_res.is_err() {
            return Ok(MatchOutcome {
                winner_id: None,
                reason: "Hòa (Cả hai bot đều gặp lỗi biên dịch / cú pháp)".to_string(),
                bot0_peak_ram_mb: 0.0,
                bot1_peak_ram_mb: 0.0,
                move_history: Vec::new(),
                initial_board: game.get_initial_state().board,
            });
        }

        if let Err(err0) = prep0_res {
            return Ok(MatchOutcome {
                winner_id: Some(1),
                reason: format!("Bot 0 lỗi biên dịch: {}", err0),
                bot0_peak_ram_mb: 0.0,
                bot1_peak_ram_mb: 0.0,
                move_history: Vec::new(),
                initial_board: game.get_initial_state().board,
            });
        }

        if let Err(err1) = prep1_res {
            return Ok(MatchOutcome {
                winner_id: Some(0),
                reason: format!("Bot 1 lỗi biên dịch: {}", err1),
                bot0_peak_ram_mb: 0.0,
                bot1_peak_ram_mb: 0.0,
                move_history: Vec::new(),
                initial_board: game.get_initial_state().board,
            });
        }

        let prep0 = prep0_res.unwrap();
        let prep1 = prep1_res.unwrap();

        let config = MatchConfig {
            timeout_per_move_ms: 1000,
            max_moves: 500,
            bot0_core,
            bot1_core,
            ram_limit_mb: 256 * 1024 * 1024,
        };

        // Gọi trực tiếp MatchRunner::run_match từ runner.rs
        let outcome = MatchRunner::run_match(config, &prep0, &prep1, game);

        let (winner_id, reason) = match outcome.result {
            crate::game_interface::MatchResult::Win { winner, reason } => (Some(winner), reason),
            crate::game_interface::MatchResult::Draw { reason } => (None, reason),
            crate::game_interface::MatchResult::Ongoing => (None, "Hết thời gian trận đấu".to_string()),
        };

        self.manager.cleanup(prep0);
        self.manager.cleanup(prep1);

        Ok(MatchOutcome {
            winner_id,
            reason,
            bot0_peak_ram_mb: (outcome.bot0_peak_ram_bytes as f64) / (1024.0 * 1024.0),
            bot1_peak_ram_mb: (outcome.bot1_peak_ram_bytes as f64) / (1024.0 * 1024.0),
            move_history: outcome.move_history,
            initial_board: outcome.initial_board,
        })
    }
}