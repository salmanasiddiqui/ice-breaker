import random
import sqlite3

from models.ice_breaker import IceBreaker


class Intellect:

    GUARANTEED_LOSS = -99999999

    @classmethod
    def get_db_conn(cls, grid_size: int):
        con = sqlite3.connect(f'icebreaker{grid_size}_bot.db')
        con.executescript("""
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
        return con

    @classmethod
    def _game_state_info(cls, game_state: str):
        bear_index = game_state.index(str(IceBreaker.BlockState.BEAR.value))
        total_indices = len(game_state)
        grid_size = int(total_indices ** 0.5)
        max_row_in_first_quarter = int(grid_size / 2) - 1
        # if grid size is odd number, then max_col_in_first_quarter will be 1 greater than max_row_in_first_quarter
        max_col_in_first_quarter = int(grid_size / 2) + (grid_size % 2) - 1

        bear_row = int(bear_index / grid_size)
        bear_col = bear_index % grid_size

        return total_indices, grid_size, max_row_in_first_quarter, max_col_in_first_quarter, bear_row, bear_col

    @classmethod
    def sanitize_game_state(cls, game_state: str, rotate: int = 0):
        """
        Rotates the game_state so that the location of Bear block is in the top-left quarter of the grid
        """
        total_indices, grid_size, max_row_in_first_quarter, max_col_in_first_quarter, bear_row, bear_col = \
            cls._game_state_info(game_state)

        if rotate == 0 and ((bear_row <= max_row_in_first_quarter and bear_col <= max_col_in_first_quarter) or
                            bear_row == bear_col == max_col_in_first_quarter):
            # bear in top-left quarter or in the center, no need to rotate grid
            return game_state

        if rotate == -1 or bear_row <= max_col_in_first_quarter < bear_col:
            # bear in top-right quarter
            row_step = -1
            col_step = grid_size
        elif rotate == 1 or bear_row > max_row_in_first_quarter >= bear_col:
            # bear in bottom-left quarter
            row_step = 1
            col_step = -grid_size
        else:
            # bear in bottom-right quarter
            row_step = -grid_size
            col_step = -1
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
    def sanitize_move(cls, game_state: str, optimal_move: int, rotate: int = 0):
        """
        Rotates the game_state so that the location of Bear block is in the top-left quarter of the grid
        """
        total_indices, grid_size, max_row_in_first_quarter, max_col_in_first_quarter, bear_row, bear_col = \
            cls._game_state_info(game_state)

        if rotate == 0 and ((bear_row <= max_row_in_first_quarter and bear_col <= max_col_in_first_quarter) or
                            bear_row == bear_col == max_col_in_first_quarter):
            # bear in top-left quarter or in the center, no need to rotate grid
            return optimal_move

        optimal_move_row = int(optimal_move / grid_size)
        optimal_move_col = optimal_move % grid_size
        if rotate == -1 or bear_row <= max_col_in_first_quarter < bear_col:
            # bear in top-right quarter
            temp = optimal_move_row
            optimal_move_row = optimal_move_col
            optimal_move_col = grid_size - 1 - temp
            return (optimal_move_row * grid_size) + optimal_move_col
        elif rotate == 1 or bear_row > max_row_in_first_quarter >= bear_col:
            # bear in bottom-left quarter
            temp = optimal_move_col
            optimal_move_col = optimal_move_row
            optimal_move_row = grid_size - 1 - temp
            return (optimal_move_row * grid_size) + optimal_move_col
        else:
            # bear in bottom-right quarter
            return total_indices - 1 - optimal_move

    @classmethod
    def get_optimal_move(cls, con: sqlite3.Connection, game_state: str, experimentation: int):
        """
        First, see if the game_state exists in the q_table or not. If it does then check possible moves that we already
        have attempted. From all attempted moves, get the moves with the highest win rate or the least games.
        Now depending on the chance of experimentation, either return one of the move with the highest win rate, or
        return the move which has not been attempted or has been attempted the least time

        Note: when experimenting, function will check whether this unattempted move will result in loss or not, if it
        will then learn this and try another unattempted move
        """
        res = con.execute('SELECT block_index, num_wins, num_games FROM q_table WHERE game_state = :game_state',
                          {'game_state': game_state}).fetchall()
        attempted_moves = []
        moves_with_highest_win_rate = [-1, []]
        moves_with_least_games = [-1, []]
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

        new_learnings = []
        if not moves_with_highest_win_rate[1] or random.randint(1, 100) <= experimentation:
            # check if there are blocks which are not yet tried
            unattempted_moves = [block_index for block_index, block_state in enumerate(game_state)
                                 if int(block_state) == IceBreaker.BlockState.ICED.value
                                 and block_index not in attempted_moves]
            i = 0
            grid_size = int(len(game_state) ** 0.5)
            while i < 15 and (unattempted_moves or moves_with_least_games[1]):
                if unattempted_moves:
                    log_message = 'unattempted'
                    random_index = random.randint(0, len(unattempted_moves) - 1)
                    move = unattempted_moves.pop(random_index)
                elif moves_with_least_games[1]:
                    log_message = 'least games'
                    random_index = random.randint(0, len(moves_with_least_games[1]) - 1)
                    move = moves_with_least_games[1].pop(random_index)
                lake_array = list(map(int, game_state))
                if IceBreaker.register_uniced_block(lake_array, move, grid_size) == -1:
                    new_learnings.append((game_state, move, cls.GUARANTEED_LOSS, -cls.GUARANTEED_LOSS))
                else:
                    break
                i += 1
            else:
                if attempted_moves:
                    log_message = 'attempted'
                    move = int(random.choice(attempted_moves))
        else:
            if moves_with_highest_win_rate[1]:
                log_message = 'optimal'
                move = int(random.choice(moves_with_highest_win_rate[1]))
            else:
                log_message = 'minimax'
                move = cls.get_minimax_move(game_state)

        if new_learnings:
            with con:
                con.executemany(
                    'INSERT OR IGNORE INTO q_table (game_state, block_index, num_wins, num_games) VALUES (?, ?, ?, ?)',
                    new_learnings
                )
        return log_message, move

    @classmethod
    def train_vs_self(cls, grid_size: int = 5, num_episodes: int = 50000, experimentation: int = 40):
        """
        For given number of episodes, make 2 bots play against each other while keeping track of q_table data. And then
        store data in q_table and q_meta table
        """
        con = cls.get_db_conn(grid_size)
        for ep in range(num_episodes):
            game_obj = IceBreaker(grid_size)
            init_state = game_obj.get_game_state()
            game_state = init_state
            while not game_obj.game_ended:
                _, chosen_block = cls.get_optimal_move(con, game_state, experimentation)
                game_obj.pick_block(game_state, chosen_block)
                game_state = game_obj.get_game_state()
            p1_won = game_obj.winner.id == game_obj.p1.id
            insert_vals = cls._get_data_for_q_table(game_obj.p1.move_per_state, p1_won)
            insert_vals += cls._get_data_for_q_table(game_obj.p2.move_per_state, not p1_won)

            with con:
                con.executemany(
                    'INSERT INTO q_table (game_state, block_index, num_wins, num_games) VALUES (?, ?, ?, ?)'
                    ' ON CONFLICT (game_state, block_index) DO UPDATE SET num_wins = num_wins + excluded.num_wins,'
                    f' num_games = num_games + excluded.num_games WHERE excluded.num_wins != {cls.GUARANTEED_LOSS}',
                    insert_vals
                )
                properties_to_increment = [(f'{init_state}_{experimentation}_games',)]
                if p1_won:
                    properties_to_increment.append((f'{init_state}_{experimentation}_wins',))
                con.executemany('INSERT INTO q_meta (property, property_val) VALUES (?, 1)'
                                ' ON CONFLICT (property) DO UPDATE SET property_val = property_val + 1',
                                properties_to_increment)
        con.execute('PRAGMA optimize')
        con.close()

    @classmethod
    def train_vs_minimax(cls, grid_size: int = 5, num_episodes: int = 50000, experimentation: int = 40):
        """
        For given number of episodes, make ML bot play against minimax bot while keeping track of q_table data. And then
        store data in q_table and q_meta table
        """
        con = cls.get_db_conn(grid_size)
        for ep in range(num_episodes):
            rotation = random.choice([-1, 0, 1, 2])
            game_obj = IceBreaker(grid_size)
            init_state = game_obj.get_game_state()
            game_state = init_state
            if ep < (num_episodes / 2):
                optimal_player_id = game_obj.p1.id
            else:
                optimal_player_id = game_obj.p2.id
            while not game_obj.game_ended:
                if game_obj.current_player.id == optimal_player_id:
                    _, chosen_block = cls.get_optimal_move(con, game_state, experimentation)
                else:
                    sanitized_game_state = cls.sanitize_game_state(game_state, rotation)
                    chosen_block = cls.get_minimax_move(sanitized_game_state)
                    chosen_block = cls.sanitize_move(sanitized_game_state, chosen_block, rotation)
                game_obj.pick_block(game_state, chosen_block)
                game_state = game_obj.get_game_state()
            optimal_won = game_obj.winner.id == optimal_player_id
            if game_obj.p1.id == optimal_player_id:
                insert_vals = cls._get_data_for_q_table(game_obj.p1.move_per_state, optimal_won)
            else:
                insert_vals = cls._get_data_for_q_table(game_obj.p2.move_per_state, optimal_won)

            with con:
                con.executemany(
                    'INSERT INTO q_table (game_state, block_index, num_wins, num_games) VALUES (?, ?, ?, ?)'
                    ' ON CONFLICT (game_state, block_index) DO UPDATE SET num_wins = num_wins + excluded.num_wins,'
                    f' num_games = num_games + excluded.num_games WHERE excluded.num_wins != {cls.GUARANTEED_LOSS}',
                    insert_vals
                )
                properties_to_increment = [(f'{init_state}_{experimentation}_p{optimal_player_id}_games',)]
                if optimal_won:
                    properties_to_increment.append((f'{init_state}_{experimentation}_p{optimal_player_id}_wins',))
                con.executemany('INSERT INTO q_meta (property, property_val) VALUES (?, 1)'
                                ' ON CONFLICT (property) DO UPDATE SET property_val = property_val + 1',
                                properties_to_increment)
        con.execute('PRAGMA optimize')
        con.close()

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

    @classmethod
    def test_optimal_vs_minimax(cls, grid_size: int, num_episodes: int = 10000, optimal_first: bool = True):
        con = cls.get_db_conn(grid_size)
        wins = 0
        for ep in range(num_episodes):
            rotation = random.choice([-1, 0, 1, 2])
            game_obj = IceBreaker(grid_size)
            game_state = game_obj.get_game_state()
            while not game_obj.game_ended:
                if bool(game_obj.current_player.id == game_obj.p1.id) == optimal_first:
                    log_msg, chosen_block = cls.get_optimal_move(con, game_state, 0)
                else:
                    sanitized_game_state = cls.sanitize_game_state(game_state, rotation)
                    chosen_block = cls.get_minimax_move(sanitized_game_state)
                    chosen_block = cls.sanitize_move(sanitized_game_state, chosen_block, rotation)
                game_obj.pick_block(game_state, chosen_block)
                game_state = game_obj.get_game_state()
            if bool(game_obj.winner.id == game_obj.p1.id) == optimal_first:
                wins += 1

        con.close()
        return wins

    @classmethod
    def get_minimax_move(cls, game_state: str):
        grid_size = int(len(game_state) ** 0.5)
        possible_moves = [block_index for block_index, block_state in enumerate(game_state)
                          if int(block_state) == IceBreaker.BlockState.ICED.value]

        best_score = -10000000
        best_move = None
        for possible_move in possible_moves:
            lake_array = list(map(int, game_state))
            score = cls._alpha_beta_minimax(lake_array, possible_move, grid_size, 10000000, 10000000, -10000000, True)
            if score > best_score:
                best_score = score
                best_move = possible_move
        return best_move

    @classmethod
    def _alpha_beta_minimax(cls, lake_array: list, picked_move: int, grid_size: int, depth: int, alpha: int, beta: int,
                            maximizing_player: bool):
        if depth == 0 or IceBreaker.register_uniced_block(lake_array, picked_move, grid_size) == -1:
            return cls._static_evaluation(maximizing_player, True)
        possible_moves = [block_index for block_index, block_state in enumerate(lake_array)
                          if block_state == IceBreaker.BlockState.ICED.value]
        if maximizing_player:
            best_score = -10000000
        else:
            best_score = 10000000
        for possible_move in possible_moves:
            test_lake_array = list(lake_array)
            score = cls._alpha_beta_minimax(test_lake_array, possible_move, grid_size, depth - 1, alpha, beta,
                                            not maximizing_player)
            if maximizing_player:
                best_score = max(best_score, score)
                alpha = max(alpha, score)
            else:
                best_score = min(best_score, score)
                beta = min(beta, score)
            if beta <= alpha:
                break
        return best_score

    @classmethod
    def _static_evaluation(cls, maximizing_player, game_over):
        if game_over:
            if maximizing_player:
                return -40
            else:
                return 40
        if maximizing_player:
            return 10
        else:
            return -10
