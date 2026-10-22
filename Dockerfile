# ── STAGE 1: Build Rust Engine ────────────────────────────────
FROM rust:slim AS engine-builder

WORKDIR /build
COPY Cargo.toml Cargo.lock* ./
COPY src ./src

# Biên dịch engine tối ưu ở chế độ release
RUN cargo build --release

# ── STAGE 2: Python Runtime Environment ──────────────────────
FROM python:3.11-slim

# Cài đặt trình biên dịch g++ cho bot C++ và các thư viện hệ thống
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài đặt dependencies Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tạo các thư mục lưu trữ dữ liệu, driver và workspace cách ly
RUN mkdir -p /app/target/release \
             /app/protocol/save/bots \
             /app/protocol/save/drivers \
             /app/workspace \
             /app/drivers

# Copy binary đã build từ Stage 1 sang và cấp quyền thực thi
COPY --from=engine-builder /build/target/release/match_runner_engine /app/target/release/match_runner_engine
RUN chmod +x /app/target/release/match_runner_engine

# Copy toàn bộ mã nguồn backend và frontend
COPY protocol/ ./protocol/
COPY frontend/ ./frontend/

# Cấu hình biến môi trường mặc định
ENV PYTHONUNBUFFERED=1 \
    PORT=10000 \
    ENGINE_BIN_PATH=/app/target/release/match_runner_engine \
    JWT_SECRET=production_secret_key_match_arena_2026

EXPOSE 10000

# Khởi chạy Uvicorn lắng nghe đúng cổng của Render
CMD ["sh", "-c", "uvicorn app:app --app-dir protocol --host 0.0.0.0 --port ${PORT:-10000}"]