import random
import json
import timeit

from ice_breaker import IceBreaker


class Intellect:

    GUARANTEED_LOSS = -99999999

    def __init__(self, grid_size: int = 5):
        self.grid_size = grid_size
        self.file_name = f'icebreaker{self.grid_size}_bot.json'
        try:
            with open(self.file_name, 'r') as f:
                self.q_table = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(e)
            self.q_table = {}

    @classmethod
    def sanitize_game_state(cls, game_state: str):
        """
        Rotates the grid so that the location of Bear block is in the top-left quarter of the grid. And returns the
        state of game as string
        """
        bear_index = game_state.index(str(IceBreaker.BlockState.BEAR.value))
        grid_size = int(len(game_state) ** 0.5)

        bear_row = int(bear_index / grid_size)
        bear_col = bear_index % grid_size
        if bear_row < grid_size / 2:
            if bear_col < int(grid_size / 2) + (grid_size % 2):
                row_step = 5
                col_step = 1
            else:
                row_step = -1
                col_step = 5
        else:
            if bear_col < int(grid_size / 2) + (grid_size % 2):
                row_step = 1
                col_step = -5
            else:
                row_step = -5
                col_step = -1
        if row_step > 0:
            row_end = 25
        else:
            row_end = -1

        new_game_str = ''
        for i in range(row_end - (grid_size * row_step), row_end, row_step):
            for k in range(0, grid_size * col_step, col_step):
                new_game_str += str(game_state[i + k])

        return new_game_str

    def train(self, num_episodes: int = 50000, experimentation: int = 40):
        """
        For given number of episodes, make 2 bots play against each other and then update q-table. And then store
        q-table in json file
        """
        for ep in range(num_episodes):
            game_obj = IceBreaker(self.grid_size)
            while not game_obj.game_ended:
                game_state = game_obj.get_game_state()
                chosen_block = self.get_optimal_move(game_state, experimentation)
                game_obj.pick_block(game_state, chosen_block)
            self._update_q_table(game_obj.p1.move_per_state, game_obj.winner.id == game_obj.p1.id)
            if game_obj.p2.move_per_state:
                self._update_q_table(game_obj.p2.move_per_state, game_obj.winner.id == game_obj.p2.id)
        with open(self.file_name, 'w') as f:
            json.dump(self.q_table, f, ensure_ascii=False, check_circular=False)

    def get_optimal_move(self, game_state: str, experimentation: int):
        """
        First, see if the game_state exists in the q-table or not. If it does then check possible moves that we already
        have attempted. From all attempted moves, get the moves with the highest win rate or the least games.
        Now depending on the chance of experimentation, either return one of the move with the highest win rate, or
        return the move which has not been attempted or has been attempted the least time
        """
        attempted_moves = []
        moves_with_highest_win_rate = [-1, []]
        moves_with_least_games = [-1, []]
        for move, move_stat in self.q_table.get(game_state, {}).items():
            attempted_moves.append(move)
            if move_stat[0] == self.GUARANTEED_LOSS:
                continue

            total_games = move_stat[1]
            win_rate = move_stat[0]/move_stat[1]
            if win_rate > moves_with_highest_win_rate[0]:
                moves_with_highest_win_rate = [win_rate, [move]]
            elif win_rate == moves_with_highest_win_rate[0]:
                moves_with_highest_win_rate[1].append(move)

            if moves_with_least_games[0] == -1 or moves_with_least_games[0] > total_games:
                moves_with_least_games = [total_games, [move]]
            elif moves_with_least_games[0] == total_games:
                moves_with_least_games[1].append(move)

        if not moves_with_highest_win_rate[1] or random.randint(1, 100) <= experimentation:
            # check if there are blocks which are not yet tried
            unattempted_moves = [block_index for block_index, block_state in enumerate(game_state)
                                 if int(block_state) != IceBreaker.BlockState.UNICED.value
                                 and block_index not in attempted_moves]
            if unattempted_moves:
                return int(random.choice(unattempted_moves))
            elif moves_with_least_games[1]:
                return int(random.choice(moves_with_least_games[1]))
            else:
                return int(random.choice(attempted_moves))
        else:
            return int(random.choice(moves_with_highest_win_rate[1]))

    def _update_q_table(self, move_per_state: list, p_won: bool):
        """
        Increment the total games count for each state, and if p has won then also increment the wins. If p has lost
        then mark the last move as guaranteed loss
        """
        for game_state, p_move in move_per_state[:-1]:
            if game_state in self.q_table and str(p_move) in self.q_table[game_state]:
                wins = self.q_table[game_state][str(p_move)][0]
                total = self.q_table[game_state][str(p_move)][1]
            else:
                wins = 0
                total = 0

            if p_won:
                wins += 1
            total += 1
            self.q_table.setdefault(game_state, {})[str(p_move)] = [wins, total]

        last_move_state, last_move = move_per_state[-1]
        if last_move_state in self.q_table and str(last_move) in self.q_table[last_move_state]:
            wins = self.q_table[last_move_state][str(last_move)][0]
            total = self.q_table[last_move_state][str(last_move)][1]
        else:
            wins = 0
            total = 0

        if p_won:
            wins += 1
            total += 1
        else:
            wins = self.GUARANTEED_LOSS
            total = -self.GUARANTEED_LOSS

        self.q_table.setdefault(last_move_state, {})[str(last_move)] = [wins, total]


def train():
    intel = Intellect(grid_size=5)
    intel.train(experimentation=100)


def get_next_move(game_state: str):
    grid_size = int(len(game_state) ** 0.5)
    sanitized_game_state = Intellect.sanitize_game_state(game_state)
    intel = Intellect(grid_size)
    return intel.get_optimal_move(sanitized_game_state, experimentation=0)


if __name__ == '__main__':
    print(timeit.repeat(train, repeat=10, number=1))
