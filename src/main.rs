// src/main.rs
mod cli;
mod engine_service;
mod game_interface;
mod process;
mod rps_game;
mod runner;
mod submission_manager;

use clap::Parser;
use cli::{Cli, Commands};
use engine_service::EngineService;
use rps_game::RPSGame;
use serde::Serialize;
use std::fs;
use std::process::exit;


#[derive(Serialize)]
struct CliResponse<T: Serialize> {
    success: bool,
    data: Option<T>,
    error: Option<String>,
}

fn main() {
    let args = Cli::parse();
    let engine = EngineService::new(&args.workspace, &args.drivers);

    match args.command {
        // LỆNH 1: Kiểm tra biên dịch / cú pháp cho một bài nộp
        Commands::Validate { sub_id, code_file, lang } => {
            let code = match fs::read_to_string(&code_file) {
                Ok(c) => c,
                Err(e) => {
                    output_json(false, None::<()>, Some(format!("Không thể đọc file {}: {}", code_file, e)));
                    exit(1);
                }
            };

            match engine.validate_code(&sub_id, &code, &lang) {
                Ok(_) => {
                    output_json(true, Some("Code hợp lệ"), None);
                    exit(0);
                }
                Err(err) => {
                    output_json(false, None::<()>, Some(err));
                    exit(1);
                }
            }
        }

        // LỆNH 2: Tiến hành trận đấu giữa 2 bot
        Commands::Duel {
            bot0_id,
            bot0_code_file,
            bot0_lang,
            bot0_core,
            bot1_id,
            bot1_code_file,
            bot1_lang,
            bot1_core,
        } => {
            let bot0_code = match fs::read_to_string(&bot0_code_file) {
                Ok(c) => c,
                Err(e) => {
                    output_json(false, None::<()>, Some(format!("Không đọc được file Bot 0: {}", e)));
                    exit(1);
                }
            };

            let bot1_code = match fs::read_to_string(&bot1_code_file) {
                Ok(c) => c,
                Err(e) => {
                    output_json(false, None::<()>, Some(format!("Không đọc được file Bot 1: {}", e)));
                    exit(1);
                }
            };

            // Khởi tạo bàn cờ mẫu
            let game = RPSGame::new();

            match engine.run_duel(
                &bot0_id,
                &bot0_code,
                &bot0_lang,
                &bot1_id,
                &bot1_code,
                &bot1_lang,
                game,
                bot0_core,
                bot1_core,
            ) {
                Ok(outcome) => {
                    // Xuất trọn vẹn kết quả trận đấu ra stdout để protocol.py hứng
                    output_json(true, Some(outcome), None);
                    exit(0);
                }
                Err(err) => {
                    output_json(false, None::<()>, Some(err));
                    exit(1);
                }
            }
        }
    }
}

/// In kết quả chuẩn định dạng JSON ra stdout
fn output_json<T: Serialize>(success: bool, data: Option<T>, error: Option<String>) {
    let resp = CliResponse { success, data, error };
    if let Ok(json_str) = serde_json::to_string(&resp) {
        println!("{}", json_str);
    }
}