import argparse

from models.intellect import Intellect


def get_optimal_move(game_state: str, experimentation: int):
    grid_size = int(len(game_state) ** 0.5)
    sanitized_game_state = Intellect.sanitize_game_state(game_state)
    intel = Intellect(grid_size)
    optimal_move = intel.get_optimal_move(sanitized_game_state, experimentation=experimentation)
    intel.con.close()
    return optimal_move


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Returns the optimal move for given state of game.')
    parser.add_argument('game_state', type=str, help='State of the game')
    parser.add_argument('--exp',
                        type=int,
                        default=0,
                        choices=list(range(0, 101, 10)),
                        help='Percent of experimentation. Default: 0')
    args = parser.parse_args()

    print(get_optimal_move(args.game_state, args.exp))
