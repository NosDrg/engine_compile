// src/submission_manager.rs
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Language {
    Python,
    Cpp,
    Java,
}

impl Language {
    
    #[warn(dead_code)]
    pub fn from_str(s: &str) -> Result<Self, String> {
        match s.to_lowercase().trim() {
            "python" | "py" | "python3" => Ok(Language::Python),
            "cpp" | "c++" => Ok(Language::Cpp),
            "java" => Ok(Language::Java),
            other => Err(format!("Ngôn ngữ không được hỗ trợ: '{}'", other)),
        }
    }
}

pub struct PreparedBot {
    #[allow(dead_code)]
    pub submission_id: String,
    pub run_dir: PathBuf,
    pub launch_cmd: String,
    pub launch_args: Vec<String>,
}

pub struct SubmissionManager {
    base_workspace: PathBuf,
    drivers_dir: PathBuf,
}

impl SubmissionManager {
    pub fn new(base_workspace: &Path, drivers_dir: &Path) -> Self {
        fs::create_dir_all(base_workspace).unwrap();
        Self {
            base_workspace: base_workspace.to_path_buf(),
            drivers_dir: drivers_dir.to_path_buf(),
        }
    }

    pub fn prepare_submission(
        &self,
        submission_id: &str,
        source_code: &str,
        lang: Language,
    ) -> Result<PreparedBot, String> {
        let bot_dir = self.base_workspace.join(submission_id);
        fs::create_dir_all(&bot_dir).map_err(|e| e.to_string())?;

        match lang {
            Language::Python => {
                fs::write(bot_dir.join("solution.py"), source_code).map_err(|e| e.to_string())?;

                let check = Command::new("python3")
                    .args(["-m", "py_compile", "solution.py"])
                    .current_dir(&bot_dir)
                    .output()
                    .map_err(|e| e.to_string())?;

                if !check.status.success() {
                    let err = String::from_utf8_lossy(&check.stderr).to_string();
                    let _ = fs::remove_dir_all(&bot_dir);
                    return Err(format!("Lỗi cú pháp Python:\n{}", err));
                }

                fs::copy(
                    self.drivers_dir.join("python/py_driver.py"),
                    bot_dir.join("py_driver.py"),
                ).map_err(|e| format!("Không tìm thấy py_driver.py: {}", e))?;

                Ok(PreparedBot {
                    submission_id: submission_id.to_string(),
                    run_dir: bot_dir,
                    launch_cmd: "python3".to_string(),
                    launch_args: vec!["-u".to_string(), "py_driver.py".to_string()],
                })
            }

            Language::Cpp => {
                fs::write(bot_dir.join("solution.cpp"), source_code).map_err(|e| e.to_string())?;
                fs::copy(
                    self.drivers_dir.join("cpp/cpp_driver.cpp"),
                    bot_dir.join("cpp_driver.cpp"),
                ).map_err(|e| format!("Không tìm thấy cpp_driver.cpp: {}", e))?;

                let compile = Command::new("g++")
                    .args(["-O3", "-std=c++17", "cpp_driver.cpp", "solution.cpp", "-o", "bot_app"])
                    .current_dir(&bot_dir)
                    .output()
                    .map_err(|e| e.to_string())?;

                if !compile.status.success() {
                    let err = String::from_utf8_lossy(&compile.stderr).to_string();
                    let _ = fs::remove_dir_all(&bot_dir);
                    return Err(format!("Lỗi biên dịch C++:\n{}", err));
                }

                Ok(PreparedBot {
                    submission_id: submission_id.to_string(),
                    run_dir: bot_dir,
                    launch_cmd: "./bot_app".to_string(),
                    launch_args: vec![],
                })
            }

            Language::Java => {
                fs::write(bot_dir.join("Solution.java"), source_code).map_err(|e| e.to_string())?;
                fs::copy(
                    self.drivers_dir.join("java/JavaDriver.java"),
                    bot_dir.join("JavaDriver.java"),
                ).map_err(|e| format!("Không tìm thấy JavaDriver.java: {}", e))?;

                let compile = Command::new("javac")
                    .args(["JavaDriver.java", "Solution.java"])
                    .current_dir(&bot_dir)
                    .output()
                    .map_err(|e| e.to_string())?;

                if !compile.status.success() {
                    let err = String::from_utf8_lossy(&compile.stderr).to_string();
                    let _ = fs::remove_dir_all(&bot_dir);
                    return Err(format!("Lỗi biên dịch Java:\n{}", err));
                }

                Ok(PreparedBot {
                    submission_id: submission_id.to_string(),
                    run_dir: bot_dir,
                    launch_cmd: "java".to_string(),
                    launch_args: vec![
                        "-Xms32m".to_string(),
                        "-Xmx256m".to_string(),
                        "-XX:+UseSerialGC".to_string(),
                        "JavaDriver".to_string(),
                    ],
                })
            }
        }
    }

    pub fn cleanup(&self, bot: PreparedBot) {
        let _ = fs::remove_dir_all(bot.run_dir);
    }
}