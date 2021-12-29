import random
import sqlite3

from models.ice_breaker import IceBreaker


class Intellect:

    GUARANTEED_LOSS = -99999999

    def __init__(self, grid_size: int = 5):
        self.grid_size = grid_size
        self.con = sqlite3.connect(f'icebreaker{self.grid_size}_bot.db')
        self.con.executescript("""
            CREATE TABLE IF NOT EXISTS q_table (
                game_state TEXT NOT NULL,
                block_index INTEGER NOT NULL,
                num_wins INTEGER NOT NULL,
                num_games INTEGER NOT NULL,
                PRIMARY KEY (game_state, block_index)
            );
            CREATE TABLE IF NOT EXISTS q_meta (property TEXT PRIMARY KEY NOT NULL, property_val INTEGER NOT NULL);
            PRAGMA journal_mode = WAL;
            PRAGMA synchronous = NORMAL;
        """)

    @classmethod
    def sanitize_game_state(cls, game_state: str):
        """
        Rotates the game_state so that the location of Bear block is in the top-left quarter of the grid
        """
        bear_index = game_state.index(str(IceBreaker.BlockState.BEAR.value))
        total_indices = len(game_state)
        grid_size = int(total_indices ** 0.5)
        max_row_in_first_quarter = int(grid_size / 2) - 1
        # if grid size is odd number, then max_col_in_first_quarter will be 1 greater than max_row_in_first_quarter
        max_col_in_first_quarter = int(grid_size / 2) + (grid_size % 2) - 1

        bear_row = int(bear_index / grid_size)
        bear_col = bear_index % grid_size

        if (bear_row <= max_row_in_first_quarter and bear_col <= max_col_in_first_quarter) or \
                bear_row == bear_col == max_col_in_first_quarter:
            # bear in top-left quarter or in the center, no need to rotate grid
            return game_state

        if bear_row <= max_col_in_first_quarter < bear_col:
            # bear in top-right quarter
            row_step = -1
            col_step = grid_size
        elif bear_row > max_col_in_first_quarter <= bear_col:
            # bear in bottom-right quarter
            row_step = -grid_size
            col_step = -1
        else:
            # bear in bottom-left quarter
            row_step = 1
            col_step = -grid_size
        if row_step > 0:
            row_end = total_indices
        else:
            row_end = -1

        new_game_str = ''
        for i in range(row_end - (grid_size * row_step), row_end, row_step):
            for k in range(0, grid_size * col_step, col_step):
                new_game_str += str(game_state[i + k])

        return new_game_str

    @classmethod
    def sanitize_move(cls, game_state: str, optimal_move: int):
        """
        Rotates the game_state so that the location of Bear block is in the top-left quarter of the grid
        """
        bear_index = game_state.index(str(IceBreaker.BlockState.BEAR.value))
        total_indices = len(game_state)
        grid_size = int(total_indices ** 0.5)
        max_row_in_first_quarter = int(grid_size / 2) - 1
        # if grid size is odd number, then max_col_in_first_quarter will be 1 greater than max_row_in_first_quarter
        max_col_in_first_quarter = int(grid_size / 2) + (grid_size % 2) - 1

        bear_row = int(bear_index / grid_size)
        bear_col = bear_index % grid_size

        if (bear_row <= max_row_in_first_quarter and bear_col <= max_col_in_first_quarter) or \
                bear_row == bear_col == max_col_in_first_quarter:
            # bear in top-left quarter or in the center, no need to rotate grid
            return optimal_move

        if bear_row > max_col_in_first_quarter <= bear_col:
            # bear in bottom-right quarter
            return total_indices - 1 - optimal_move
        else:
            optimal_move_row = int(optimal_move / grid_size)
            optimal_move_col = optimal_move % grid_size
            if bear_row <= max_col_in_first_quarter < bear_col:
                # bear in bottom-left quarter
                temp = optimal_move_row
                optimal_move_row = optimal_move_col
                optimal_move_col = grid_size - 1 - temp
            else:
                # bear in top-right quarter
                temp = optimal_move_col
                optimal_move_col = optimal_move_row
                optimal_move_row = grid_size - 1 - temp

            return (optimal_move_row * grid_size) + optimal_move_col

    def get_optimal_move(self, game_state: str, experimentation: int):
        """
        First, see if the game_state exists in the q_table or not. If it does then check possible moves that we already
        have attempted. From all attempted moves, get the moves with the highest win rate or the least games.
        Now depending on the chance of experimentation, either return one of the move with the highest win rate, or
        return the move which has not been attempted or has been attempted the least time
        """
        attempted_moves = []
        moves_with_highest_win_rate = [-1, []]
        moves_with_least_games = [-1, []]
        res = self.con.execute('SELECT block_index, num_wins, num_games FROM q_table WHERE game_state = :game_state',
                               {'game_state': game_state})
        for move, num_wins, num_games in res:
            attempted_moves.append(move)
            if num_wins < 0:
                continue

            win_rate = num_wins/num_games
            if win_rate > moves_with_highest_win_rate[0]:
                moves_with_highest_win_rate = [win_rate, [move]]
            elif win_rate == moves_with_highest_win_rate[0]:
                moves_with_highest_win_rate[1].append(move)

            if moves_with_least_games[0] == -1 or moves_with_least_games[0] > num_games:
                moves_with_least_games = [num_games, [move]]
            elif moves_with_least_games[0] == num_games:
                moves_with_least_games[1].append(move)

        if not moves_with_highest_win_rate[1] or random.randint(1, 100) <= experimentation:
            # check if there are blocks which are not yet tried
            unattempted_moves = [block_index for block_index, block_state in enumerate(game_state)
                                 if int(block_state) == IceBreaker.BlockState.ICED.value
                                 and block_index not in attempted_moves]
            if unattempted_moves:
                return int(random.choice(unattempted_moves))
            elif moves_with_least_games[1]:
                return int(random.choice(moves_with_least_games[1]))
            else:
                return int(random.choice(attempted_moves))
        else:
            return int(random.choice(moves_with_highest_win_rate[1]))

    def train(self, num_episodes: int = 50000, experimentation: int = 40):
        """
        For given number of episodes, make 2 bots play against each other while keeping track of q_table data. And then
        store data in q_table and q_meta table
        """
        for ep in range(num_episodes):
            game_obj = IceBreaker(self.grid_size)
            init_state = game_obj.get_game_state()
            game_state = init_state
            while not game_obj.game_ended:
                chosen_block = self.get_optimal_move(game_state, experimentation)
                game_obj.pick_block(game_state, chosen_block)
                game_state = game_obj.get_game_state()
            p1_won = game_obj.winner.id == game_obj.p1.id
            insert_vals = self._get_data_for_q_table(game_obj.p1.move_per_state, p1_won)
            insert_vals += self._get_data_for_q_table(game_obj.p2.move_per_state, not p1_won)

            with self.con:
                self.con.executemany(
                    'INSERT INTO q_table (game_state, block_index, num_wins, num_games) VALUES (?, ?, ?, ?)'
                    ' ON CONFLICT (game_state, block_index) DO UPDATE SET num_wins = num_wins + excluded.num_wins,'
                    f' num_games = num_games + excluded.num_games WHERE excluded.num_wins != {self.GUARANTEED_LOSS}',
                    insert_vals
                )
                properties_to_increment = [(f'{init_state}_{experimentation}_games',)]
                if p1_won:
                    properties_to_increment.append((f'{init_state}_{experimentation}_wins',))
                self.con.executemany('INSERT INTO q_meta (property, property_val) VALUES (?, 1)'
                                     ' ON CONFLICT (property) DO UPDATE SET property_val = property_val + 1',
                                     properties_to_increment)

    @classmethod
    def _get_data_for_q_table(cls, move_per_state: list, p_won: bool):
        """
        Increment the total games count for each state, and if p has won then also increment the wins. If p has lost
        then mark the last move as guaranteed loss
        """
        last_move_index = len(move_per_state) - 1
        insert_data = []
        wins = int(p_won)
        for i, (game_state, p_move) in enumerate(move_per_state):
            if i == last_move_index and not p_won:
                insert_data.append((game_state, p_move, cls.GUARANTEED_LOSS, -cls.GUARANTEED_LOSS))
            else:
                insert_data.append((game_state, p_move, wins, 1))

        return insert_data
