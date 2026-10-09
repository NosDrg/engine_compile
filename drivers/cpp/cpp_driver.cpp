#include <iostream>
#include <string>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

extern json get_move(const json& state);

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        if (line == "QUIT") break;

        try {
            json state = json::parse(line);

            json move = get_move(state);

            std::cout << move.dump() << "\n" << std::flush;
        } catch (const std::exception& e) {
            std::cerr << "RUNTIME_ERROR: " << e.what() << "\n";
            std::cout << "__CRASH__\n" << std::flush;
        } catch (...) {
            std::cerr << "RUNTIME_ERROR: Lỗi không xác định trong mã C++\n";
            std::cout << "__CRASH__\n" << std::flush;
        }
    }
    return 0;
}