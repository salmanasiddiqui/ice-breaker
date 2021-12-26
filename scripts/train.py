import timeit

from models.intellect import Intellect


def train():
    intel = Intellect(grid_size=6)
    intel.train(experimentation=40)
    intel.con.close()


def get_next_move(game_state: str):
    grid_size = int(len(game_state) ** 0.5)
    sanitized_game_state = Intellect.sanitize_game_state(game_state)
    intel = Intellect(grid_size)
    optimal_move = intel.get_optimal_move(sanitized_game_state, experimentation=0)
    intel.con.close()
    return optimal_move


if __name__ == '__main__':
    print(timeit.repeat(train, repeat=10, number=1))
