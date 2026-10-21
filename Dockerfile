# ── STAGE 1: Build Rust Engine ────────────────────────────────
FROM rust:slim AS engine-builder

WORKDIR /build
# Copy Cargo manifests để cache dependency
COPY Cargo.toml Cargo.lock* ./
# Copy mã nguồn Rust (thư mục src của engine)
COPY src ./src

# Build binary ở chế độ tối ưu hóa release
RUN cargo build --release

# ── STAGE 2: Python Runtime Environment ──────────────────────
FROM python:3.11-slim

# Cài đặt trình biên dịch/runtime để chạy bot (g++, openjdk, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài đặt Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy binary engine từ Stage 1
COPY --from=engine-builder /build/target/release/ /app/engine/

# Copy mã nguồn Backend & Frontend
COPY protocol/ ./protocol/
COPY frontend/ ./frontend/

# Tạo sẵn thư mục lưu database và bot source code
RUN mkdir -p /app/protocol/save/bots

# Cấu hình biến môi trường mặc định
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    BOTS_STORAGE_DIR=/app/protocol/save/bots \
    JWT_SECRET=super_secret_match_arena_jwt_key_2026

EXPOSE 8000

# Chạy Uvicorn hỗ trợ biến $PORT động trên cloud (Render/Fly.io)
CMD ["sh", "-c", "uvicorn app:app --app-dir protocol --host 0.0.0.0 --port ${PORT:-8000}"]