use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

pub struct PreparedBot {
    pub submission_id: String,
    pub run_dir: PathBuf,
}

pub struct SubmissionManager {
    base_workspace: PathBuf,
    driver_template_path: PathBuf,
}

impl SubmissionManager {
    pub fn new(base_workspace: &Path, driver_template_path: &Path) -> Self {
        fs::create_dir_all(base_workspace).unwrap();
        Self {
            base_workspace: base_workspace.to_path_buf(),
            driver_template_path: driver_template_path.to_path_buf(),
        }
    }

    /// Nhận chuỗi code trực tiếp từ giao thức và chuẩn bị môi trường chạy
    pub fn prepare_submission(
        &self,
        submission_id: &str,
        source_code: &str,
    ) -> Result<PreparedBot, String> {
        let bot_dir = self.base_workspace.join(submission_id);
        fs::create_dir_all(&bot_dir).map_err(|e| e.to_string())?;

        // 1. Ghi file solution.py
        let solution_path = bot_dir.join("solution.py");
        fs::write(&solution_path, source_code).map_err(|e| e.to_string())?;

        // 2. Kiểm tra cú pháp (Compile Check)
        let compile_check = Command::new("python3")
            .arg("-m")
            .arg("py_compile")
            .arg("solution.py")
            .current_dir(&bot_dir)
            .output();

        match compile_check {
            Ok(output) if !output.status.success() => {
                let err_msg = String::from_utf8_lossy(&output.stderr).to_string();
                let _ = fs::remove_dir_all(&bot_dir);
                return Err(format!("Lỗi cú pháp (Compilation Error): {}", err_msg));
            }
            Err(e) => return Err(format!("Không thể kiểm tra cú pháp: {}", e)),
            _ => {}
        }

        // 3. Nạp file py_driver.py ẩn của hệ thống vào thư mục chạy
        let driver_dest = bot_dir.join("py_driver.py");
        fs::copy(&self.driver_template_path, driver_dest).map_err(|e| e.to_string())?;

        Ok(PreparedBot {
            submission_id: submission_id.to_string(),
            run_dir: bot_dir,
        })
    }

    /// Dọn dẹp thư mục sau khi trận đấu hoàn tất
    pub fn cleanup(&self, bot: PreparedBot) {
        let _ = fs::remove_dir_all(bot.run_dir);
    }
}