# ── STAGE 1: Build Rust Engine ────────────────────────────────
FROM rust:slim AS engine-builder

WORKDIR /build
COPY Cargo.toml Cargo.lock* ./
COPY src ./src

# Build binary ở chế độ tối ưu hóa release
RUN cargo build --release

# ── STAGE 2: Python Runtime Environment ──────────────────────
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài đặt Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tạo sẵn thư mục target/release đúng như adapter.py tìm kiếm
RUN mkdir -p /app/target/release /app/protocol/save/bots

# Copy chính xác file binary từ builder sang và cấp quyền chạy
COPY --from=engine-builder /build/target/release/match_runner_engine /app/target/release/match_runner_engine
RUN chmod +x /app/target/release/match_runner_engine

# Copy mã nguồn Backend & Frontend
COPY protocol/ ./protocol/
COPY frontend/ ./frontend/

ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    BOTS_STORAGE_DIR=/app/protocol/save/bots \
    ENGINE_BIN_PATH=/app/target/release/match_runner_engine \
    JWT_SECRET=super_secret_match_arena_jwt_key_2026

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --app-dir protocol --host 0.0.0.0 --port ${PORT:-8000}"]