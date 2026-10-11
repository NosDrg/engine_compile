// src/cli.rs
use clap::{Parser, Subcommand};

#[derive(Parser, Debug)]
#[command(name = "match_runner_engine")]
#[command(about = "Engine runner an toàn cho game Rock-Paper-Scissors 9x9", long_about = None)]
pub struct Cli {
    #[arg(short, long, default_value = "./workspace")]
    pub workspace: String,

    #[arg(short, long, default_value = "./drivers")]
    pub drivers: String,

    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand, Debug)]
pub enum Commands {
    Validate {
        #[arg(long)]
        sub_id: String,

        #[arg(long)]
        code_file: String,

        #[arg(long)]
        lang: String,
    },

    Duel {
        #[arg(long)]
        bot0_id: String,
        #[arg(long)]
        bot0_code_file: String,
        #[arg(long)]
        bot0_lang: String,
        #[arg(long, default_value_t = 0)]
        bot0_core: usize,

        #[arg(long)]
        bot1_id: String,
        #[arg(long)]
        bot1_code_file: String,
        #[arg(long)]
        bot1_lang: String,
        #[arg(long, default_value_t = 1)]
        bot1_core: usize,
    },
}