# drivers/python/py_driver.py
import sys
import json

try:
    import solution # type: ignore
except Exception as e:
    sys.stderr.write(f"IMPORT_ERROR: {e}\n")
    sys.exit(1)

def main():
    while True:
        raw_input = sys.stdin.readline()
        if not raw_input:
            break
        raw_input = raw_input.strip()
        if raw_input == "QUIT":
            break

        try:
            # Parse state từ Rust Engine gửi sang
            state_data = json.loads(raw_input)
            
            # Gọi hàm của thí sinh
            move = solution.get_move(state_data)
            
            # Chuẩn hóa về chuỗi JSON hợp lệ với nháy kép
            if isinstance(move, dict):
                move_str = json.dumps(move)
            elif isinstance(move, str):
                clean_move = move.strip()
                if clean_move.startswith("{") and "'" in clean_move:
                    import ast
                    parsed_dict = ast.literal_eval(clean_move)
                    move_str = json.dumps(parsed_dict)
                else:
                    move_str = clean_move
            else:
                move_str = json.dumps(move)

            sys.stdout.write(f"{move_str}\n")
            sys.stdout.flush()
        except Exception as err:
            sys.stderr.write(f"RUNTIME_ERROR: {err}\n")
            sys.stdout.write("__CRASH__\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()