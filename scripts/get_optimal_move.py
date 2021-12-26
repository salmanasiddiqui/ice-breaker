import argparse

from models.intellect import Intellect


def get_next_move(game_state: str):
    grid_size = int(len(game_state) ** 0.5)
    sanitized_game_state = Intellect.sanitize_game_state(game_state)
    intel = Intellect(grid_size)
    optimal_move = intel.get_optimal_move(sanitized_game_state, experimentation=0)
    intel.con.close()
    return optimal_move


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Returns the optimal move for given state of game.')
    parser.add_argument('game_state', type=str, help='State of the game')
    args = parser.parse_args()

    print(get_next_move(args.game_state))
