# Engine Compile

Engine chạy trận đấu cho game Rock–Paper–Scissors 9x9, hỗ trợ validate và duel giữa các bot viết bằng Python, C++ và Java.

## Yêu cầu hệ thống

Trước khi chạy, hãy đảm bảo máy đã cài đặt:

- Rust toolchain: `rustc` và `cargo`
- Python 3: `python3`
- C++ compiler: `g++`
- Java compiler: `javac`

Bạn có thể kiểm tra nhanh với:

```bash
rustc --version
python3 --version
g++ --version
javac -version
```

## Cấu trúc thư mục cần thiết

Project mặc định mong đợi hai thư mục:

- `./workspace` : nơi engine tạo thư mục làm việc tạm cho từng bot khi compile và chạy
- `./drivers` : nơi chứa file driver mẫu cho từng ngôn ngữ

Cấu trúc bắt buộc trong `drivers`:

```text
drivers/
├── python/
│   └── py_driver.py
├── cpp/
│   └── cpp_driver.cpp
├── java/
│   └── JavaDriver.java
└── ...
```

Nếu bạn đặt thư mục ở vị trí khác, hãy truyền tham số `--workspace` và `--drivers` khi chạy CLI.

## Cấu hình chạy

CLI định nghĩa như sau:

```bash
cargo run -- --workspace <path/to/workspace> --drivers <path/to/drivers> <command>
```

### 1) Validate một bot

```bash
cargo run -- --workspace ./workspace --drivers ./drivers validate \
  --sub_id demo_bot \
  --code_file ./examples/solution.py \
  --lang python
```

- `sub_id`: mã định danh tạm cho bài nộp
- `code_file`: đường dẫn đến file source
- `lang`: `python`, `py`, `cpp`, `c++`, hoặc `java`

Nếu source hợp lệ, engine sẽ compile/validate và trả về JSON thành công.

### 2) Chạy duel giữa 2 bot

```bash
cargo run -- --workspace ./workspace --drivers ./drivers duel \
  --bot0_id bot_a \
  --bot0_code_file ./examples/bot_a.py \
  --bot0_lang python \
  --bot0_core 0 \
  --bot1_id bot_b \
  --bot1_code_file ./examples/bot_b.cpp \
  --bot1_lang cpp \
  --bot1_core 1
```

Các tham số quan trọng:

- `--bot0_core`, `--bot1_core`: gán CPU core cho từng bot
- `--bot0_lang`, `--bot1_lang`: ngôn ngữ tương ứng
- `--workspace` phải là thư mục có thể ghi để engine tạo môi trường chạy tạm
- `--drivers` phải trỏ đến thư mục chứa file driver chuẩn của project

## Ví dụ cấu hình tối thiểu

Nếu bạn dùng cấu trúc mặc định, chỉ cần chạy:

```bash
cargo run -- validate --sub_id sample --code_file ./solution.py --lang python
```

hoặc:

```bash
cargo run -- duel \
  --bot0_id red \
  --bot0_code_file ./bot_red.py \
  --bot0_lang python \
  --bot1_id blue \
  --bot1_code_file ./bot_blue.java \
  --bot1_lang java
```

## Lưu ý quan trọng

- Engine sẽ tạo thư mục con bên trong `workspace` theo `submission_id` và xóa sau khi hoàn tất.
- `drivers` không phải thư mục rỗng; nó cần chứa các file `py_driver.py`, `cpp_driver.cpp`, `JavaDriver.java`.
- Nếu không có `python3`, `g++` hoặc `javac` trên PATH, các lệnh validate/duel sẽ thất bại.
- Kết quả trả về ở định dạng JSON trên stdout để backend hoặc protocol có thể đọc tiếp.

## Build nhanh

```bash
cargo build --release
```

Sau khi build xong, bạn có thể chạy binary đã compile trực tiếp:

```bash
./target/release/match_runner_engine --help
```

