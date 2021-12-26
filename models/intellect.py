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
        """)

    @classmethod
    def sanitize_game_state(cls, game_state: str):
        """
        Rotates the game_state so that the location of Bear block is in the top-left quarter of the grid
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
        For given number of episodes, make 2 bots play against each other while keeping track of q_table data. And then
        store data in q_table and q_meta table
        """
        cursor = self.con.cursor()
        q_table_data = {}
        for ep in range(num_episodes):
            game_obj = IceBreaker(self.grid_size)
            while not game_obj.game_ended:
                game_state = game_obj.get_game_state()
                chosen_block = self.get_optimal_move(game_state, experimentation, cursor)
                game_obj.pick_block(game_state, chosen_block)
            self._update_q_table(q_table_data, game_obj.p1.move_per_state, game_obj.winner.id == game_obj.p1.id)
            self._update_q_table(q_table_data, game_obj.p2.move_per_state, game_obj.winner.id == game_obj.p2.id)
        cursor.close()

        insert_vals = []
        for game_state, move_and_stats in q_table_data.items():
            for move, move_stats in move_and_stats.items():
                insert_vals.append((game_state, move, move_stats[0], move_stats[1]))
        del q_table_data

        with self.con:
            self.con.executemany('INSERT INTO q_table (game_state, block_index, num_wins, num_games)'
                                 ' VALUES (?, ?, ?, ?) ON CONFLICT (game_state, block_index) DO UPDATE SET'
                                 ' num_wins = num_wins + excluded.num_wins, num_games = num_games + excluded.num_games',
                                 insert_vals)
            res = self.con.execute('UPDATE q_meta SET property_val=property_val+:num_eps WHERE property="num_games"',
                                   {'num_eps': num_episodes})
            if res.rowcount == 0:
                self.con.execute('INSERT INTO q_meta (property, property_val) VALUES ("num_games", :num_eps)',
                                 {'num_eps': num_episodes})

    def get_optimal_move(self, game_state: str, experimentation: int, cursor: sqlite3.Cursor = None):
        """
        First, see if the game_state exists in the q_table or not. If it does then check possible moves that we already
        have attempted. From all attempted moves, get the moves with the highest win rate or the least games.
        Now depending on the chance of experimentation, either return one of the move with the highest win rate, or
        return the move which has not been attempted or has been attempted the least time
        """
        attempted_moves = []
        moves_with_highest_win_rate = [-1, []]
        moves_with_least_games = [-1, []]
        select_q = f'SELECT block_index, num_wins, num_games FROM q_table WHERE game_state = :game_state'
        if cursor:
            res = cursor.execute(select_q, {'game_state': game_state})
        else:
            res = self.con.execute(select_q, {'game_state': game_state})
        for move, num_wins, num_games in res:
            attempted_moves.append(move)
            if num_wins == self.GUARANTEED_LOSS:
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

    @classmethod
    def _update_q_table(cls, q_table_data, move_per_state: list, p_won: bool):
        """
        Increment the total games count for each state, and if p has won then also increment the wins. If p has lost
        then mark the last move as guaranteed loss
        """
        last_move_index = len(move_per_state) - 1
        for i, (game_state, p_move) in enumerate(move_per_state):
            q_table_data.setdefault(game_state, {}).setdefault(p_move, [0, 0])
            if i == last_move_index and not p_won:
                q_table_data[game_state][p_move] = [cls.GUARANTEED_LOSS, -cls.GUARANTEED_LOSS]
            else:
                if p_won:
                    q_table_data[game_state][p_move][0] += 1
                q_table_data[game_state][p_move][1] += 1
