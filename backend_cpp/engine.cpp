#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <string>
#include <map>
#include <vector>
#include <algorithm>

namespace py = pybind11;

struct Player {
    std::string id;
    std::string name;
    int score;
    int streak;
};

class GameEngine {
private:
    std::map<std::string, Player> players;

public:
    GameEngine() {}

    // Add Player: Returns "Joined" or "Reconnect"
    std::string add_player(std::string id, std::string name) {
        if (players.find(id) != players.end()) {
            return "Reconnect";
        }
        players[id] = {id, name, 0, 0};
        return "Joined";
    }

    // Remove Player
    void remove_player(std::string id) {
        players.erase(id);
    }

    // Score Calculation: 
    // Base(1000) + (TimeLeft * 100) + (Streak * 50)
    int update_score(std::string id, bool correct, float time_left) {
        if (players.find(id) == players.end()) return 0;

        if (correct) {
            int points = 1000 + (int)(time_left * 100) + (players[id].streak * 50);
            players[id].score += points;
            players[id].streak++;
        } else {
            players[id].streak = 0; // Reset streak on fail
        }
        return players[id].score;
    }

    // Get Leaderboard: Returns a sorted list of [Name, Score]
    std::vector<std::pair<std::string, int>> get_leaderboard() {
        std::vector<std::pair<std::string, int>> leaderboard;
        for (auto const& [key, val] : players) {
            leaderboard.push_back({val.name, val.score});
        }
        
        // Sort descending (Highest score first)
        std::sort(leaderboard.begin(), leaderboard.end(), 
            [](const std::pair<std::string, int> &a, const std::pair<std::string, int> &b) {
                return a.second > b.second;
            });
        
        return leaderboard;
    }
};

// Python Binding Code
PYBIND11_MODULE(quiz_engine, m) {
    py::class_<GameEngine>(m, "GameEngine")
        .def(py::init<>())
        .def("add_player", &GameEngine::add_player)
        .def("remove_player", &GameEngine::remove_player)
        .def("update_score", &GameEngine::update_score)
        .def("get_leaderboard", &GameEngine::get_leaderboard);
}