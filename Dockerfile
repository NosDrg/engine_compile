# ==========================================
# GIAI ĐOẠN 1: Biên dịch Rust Engine
# ==========================================
# Thay rust:1.80-slim bằng rust:slim (tự động lấy phiên bản Rust mới nhất)
FROM rust:slim AS builder

WORKDIR /usr/src/engine

# Cài đặt các công cụ C cần thiết cho build script
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy file cấu hình Cargo và mã nguồn Rust
COPY Cargo.toml Cargo.lock ./
COPY src/ ./src/

# Biên dịch binary release
RUN cargo build --release

# ==========================================
# GIAI ĐOẠN 2: Môi trường chạy FastAPI & Sandbox
# ==========================================
FROM python:3.11-slim

# Cài đặt môi trường runtime cho các bot
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    default-jre-headless \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài đặt các gói Python
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pydantic \
    psutil

# Copy Rust Engine binary từ Giai đoạn 1
COPY --from=builder /usr/src/engine/target/release/match_runner_engine /app/target/release/match_runner_engine
RUN chmod +x /app/target/release/match_runner_engine

# Tạo các thư mục cần thiết
RUN mkdir -p /app/workspace /app/drivers /app/frontend

# Copy mã nguồn backend, frontend và drivers
COPY protocol/ /app/protocol/
COPY frontend/ /app/frontend/
COPY drivers/ /app/drivers/

ENV PYTHONPATH=/app/protocol
ENV PYTHONUNBUFFERED=1

WORKDIR /app/protocol

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]