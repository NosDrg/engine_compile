# ----------------- STAGE 1: Build Rust Engine -----------------
FROM rust:latest AS builder

WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src ./src

# Biên dịch binary release
RUN cargo build --release

# ----------------- STAGE 2: Runtime Environment -----------------
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    default-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/target/release/match_runner_engine ./target/release/match_runner_engine

COPY protocol ./protocol
COPY frontend ./frontend
COPY drivers ./drivers

RUN pip install --no-cache-dir fastapi uvicorn pydantic

RUN mkdir -p /app/workspace

EXPOSE 8000

WORKDIR /app/protocol
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]