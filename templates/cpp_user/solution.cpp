#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

json get_move(const json& state) {
    // SOLUTION


    return {
        {"from_x", 0},
        {"from_y", 0},
        {"to_x", 0},
        {"to_y", 1}
    };
}