// src/process.rs
use nix::poll::{poll, PollFd, PollFlags, PollTimeout};
use nix::sched::{sched_setaffinity, CpuSet};
use nix::sys::resource::{setrlimit, Resource};
use nix::unistd::Pid;
use std::io::{BufRead, BufReader, Write};
use std::os::fd::AsFd;
use std::os::unix::process::CommandExt;
use std::path::Path;
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::time::{Duration, Instant};

#[derive(Debug)]
pub enum BotError {
    Timeout(Duration),
    RuntimeCrash(String),
    BrokenPipe,
    IOError(String),
}

pub struct BotProcess {
    pub player_id: usize,
    child: Child,
    stdin: ChildStdin,
    stdout_reader: BufReader<ChildStdout>,
}

impl BotProcess {
    pub fn spawn(
        player_id: usize,
        bot_folder: &Path,
        launch_cmd: &str,
        launch_args: &[String],
        core_id: usize,
        ram_limit_mb: u64,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let ram_bytes = ram_limit_mb * 1024 * 1024;

        let mut cmd = Command::new(launch_cmd);
        cmd.args(launch_args)
            .current_dir(bot_folder)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        unsafe {
            cmd.pre_exec(move || {
                // 1. Ghim Core CPU (CPU Pinning)
                let mut cpuset = CpuSet::new();
                if cpuset.set(core_id).is_err() {
                    return Err(std::io::Error::last_os_error());
                }
                if sched_setaffinity(Pid::from_raw(0), &cpuset).is_err() {
                    return Err(std::io::Error::last_os_error());
                }

                // 2. Khóa trần RAM tối đa
                if setrlimit(Resource::RLIMIT_AS, ram_bytes, ram_bytes).is_err() {
                    return Err(std::io::Error::last_os_error());
                }

                Ok(())
            });
        }

        let mut child = cmd.spawn()?;
        let stdin = child.stdin.take().ok_or("Failed to open stdin")?;
        let stdout = child.stdout.take().ok_or("Failed to open stdout")?;
        let stdout_reader = BufReader::new(stdout);

        Ok(Self {
            player_id,
            child,
            stdin,
            stdout_reader,
        })
    }

    pub fn send_state(&mut self, state_str: &str) -> Result<(), BotError> {
        writeln!(self.stdin, "{}", state_str).map_err(|_| BotError::BrokenPipe)?;
        self.stdin.flush().map_err(|_| BotError::BrokenPipe)
    }

    /// Đọc nước đi sử dụng poll(2) trực tiếp - zero thread overhead
    pub fn get_move_fast(&mut self, timeout: Duration) -> Result<(String, Duration), BotError> {
        let start = Instant::now();
        let fd = self.stdout_reader.get_ref().as_fd();

        let mut poll_fds = [PollFd::new(fd, PollFlags::POLLIN)];
        
        let timeout_ms: u64 = timeout.as_millis() as u64;
        let poll_timeout = PollTimeout::try_from(timeout_ms)
            .map_err(|e| BotError::IOError(format!("Timeout không hợp lệ: {:?}", e)))?;

        match poll(&mut poll_fds, poll_timeout) {
            Ok(0) => Err(BotError::Timeout(timeout)),
            Ok(_) => {
                let mut line = String::new();
                match self.stdout_reader.read_line(&mut line) {
                    Ok(0) => Err(BotError::BrokenPipe),
                    Ok(_) => {
                        let elapsed = start.elapsed();
                        let clean = line.trim().to_string();
                        if clean == "__CRASH__" {
                            Err(BotError::RuntimeCrash("Lỗi runtime trong hàm thí sinh".to_string()))
                        } else {
                            Ok((clean, elapsed))
                        }
                    }
                    Err(e) => Err(BotError::IOError(e.to_string())),
                }
            }
            Err(e) => Err(BotError::IOError(e.to_string())),
        }
    }

    pub fn terminate(&mut self) {
        let _ = writeln!(self.stdin, "QUIT");
        let _ = self.stdin.flush();
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

impl Drop for BotProcess {
    fn drop(&mut self) {
        self.terminate();
    }
}