def get_move(board_data: str) -> str:
    # Tạo danh sách tiêu tốn hơn 1GB RAM
    # Khi vượt quá 256MB, Linux Kernel sẽ từ chối cấp phát bộ nhớ
    leak_memory = []
    for _ in range(100):
        # Mỗi chuỗi chiếm ~50MB RAM
        leak_memory.append("A" * (50 * 1024 * 1024))
    
    return "memory_leaker"