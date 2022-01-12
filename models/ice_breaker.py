import random

from enum import IntEnum


class IceBreaker:

    class BlockState(IntEnum):
        UNICED = 0
        ICED = 1
        BEAR = 2

    class Player:

        def __init__(self, player_id: int):
            self.id = player_id
            self.move_per_state = []

    def __init__(self, grid_size: int):
        assert 3 < grid_size < 10
        self.grid_size = grid_size
        self.game_ended = False
        self.lake_array = [self.BlockState.ICED.value] * (grid_size ** 2)
        max_bear_row_index = int(grid_size / 2) - 1
        # for odd grid size, max_bear_col_index will be 1 greater than max_bear_row_index
        max_bear_col_index = int(grid_size / 2) + (grid_size % 2) - 1
        bear_row = random.randint(0, max_bear_col_index)
        if bear_row > max_bear_row_index:
            bear_col = bear_row  # bear at the center of odd grid size
        else:
            bear_col = random.randint(0, max_bear_col_index)
        bear_index = (bear_row * grid_size) + bear_col
        self.lake_array[bear_index] = self.BlockState.BEAR.value
        self.p1 = self.Player(1)
        self.p2 = self.Player(2)
        self.current_player = None
        self.winner = None

    def get_game_state(self):
        return ''.join(map(str, self.lake_array))

    def pretty_print(self):
        [print(self.lake_array[i * self.grid_size:(i + 1) * self.grid_size]) for i in range(self.grid_size)]
        print(f"Game Ended: {self.game_ended}")

    def pick_block(self, game_state: str, block_index: int):
        if self.game_ended:
            return
        if not self.current_player or self.current_player.id != self.p1.id:
            self.current_player = self.p1
        else:
            self.current_player = self.p2
        self.current_player.move_per_state.append([game_state, block_index])
        if self.register_uniced_block(self.lake_array, block_index, self.grid_size) == -1:
            self.game_ended = True
        if self.game_ended:
            if self.current_player.id == self.p1.id:
                self.winner = self.p2
            else:
                self.winner = self.p1

    @classmethod
    def register_uniced_block(cls, lake_array: list, block_index: int, grid_size: int = None):
        """
        Registers the block_index as uniced. This may result in collapsing other blocks
        Returns:
            (int|None) -1 if game ended otherwise None
        """
        if not grid_size:
            grid_size = int(len(lake_array) ** 0.5)
        if lake_array[block_index] != cls.BlockState.ICED.value:
            return -1
        lake_array[block_index] = cls.BlockState.UNICED.value
        return cls._collapse_surrounding_blocks(lake_array, block_index, grid_size)

    @classmethod
    def _collapse_surrounding_blocks(cls, lake_array: list, block_index: int, grid_size: int):
        """
        Collapses surrounding blocks. The logic to collapse is if any of the diagonal block is uniced, then the common
        adjacent blocks should be collapsed
        example:
        Consider the below grid in f1, where `u` is uniced block, and `o` is the block_index
             f1                    f2
          - - - - -             - - - - -
          - u - - -             - u c - -
          - - o - -             - c o - -
          - - - - -             - - - - -
          - - - - -             - - - - -
        as `o` has  diagonal uniced block, the common adjacent blocks should be collapsed. `c` are common adjacent
        blocks in f2. Lets unice `o` and unice one of the common adjacent. And then follow the same logic again for that
        (2row,3col) block
          - - - - -
          - u u - -
          - c u - -
          - - - - -
          - - - - -
        check the diagonal uniced block to `u` (2row,3col). There are none, hence no collapsing for this action. Now
        collapse the other common adjacent block (3row,2col)
          - - - - -
          - u u - -
          - u u - -
          - - - - -
          - - - - -
        lets check the diagonal uniced block to `u` (3row,2col). There is one (2row,3col). So we again get the common
        adjacent blocks (2row,2col),(3row,3col) but they are already uniced so no need to collapse them
        """
        diagonal_uniced_block_indices = cls._get_diagonal_uniced_block_indices(lake_array, block_index, grid_size)

        adjacent_iced_block_indices = []
        for diagonal_uniced_block_index in diagonal_uniced_block_indices:
            if diagonal_uniced_block_index < block_index:
                first_adjacent_block_index = block_index - grid_size
            else:
                first_adjacent_block_index = block_index + grid_size
            if diagonal_uniced_block_index < first_adjacent_block_index:
                second_adjacent_block_index = block_index - 1
            else:
                second_adjacent_block_index = block_index + 1

            for adjacent_block_index in [first_adjacent_block_index, second_adjacent_block_index]:
                if lake_array[adjacent_block_index] == cls.BlockState.UNICED.value:
                    continue

                if adjacent_block_index not in adjacent_iced_block_indices:
                    adjacent_iced_block_indices.append(adjacent_block_index)

        for adjacent_block_index in adjacent_iced_block_indices:
            if cls.register_uniced_block(lake_array, adjacent_block_index, grid_size) == -1:
                return -1

    @classmethod
    def _get_diagonal_uniced_block_indices(cls, lake_array: list, block_index: int, grid_size: int):
        """
        Returns index of uniced blocks diagonal to given block_index
        Considering the grid below, if `o` is the block_index, then the state of `x` blocks will be checked and returned
        if they are all uniced
          - - - - -
          - x - x -
          - - o - -
          - x - x -
          - - - - -
        """
        row = int(block_index / grid_size)
        col = block_index % grid_size

        rows_to_look = []
        if row > 0:
            rows_to_look.append(row - 1)
        if row < grid_size - 1:
            rows_to_look.append(row + 1)

        diagonal_uniced_block_indices = []
        for current_row in rows_to_look:
            if col > 0:
                diagonal_block_index = (current_row * grid_size) + col - 1
                if lake_array[diagonal_block_index] == cls.BlockState.UNICED.value:
                    diagonal_uniced_block_indices.append(diagonal_block_index)
            if col < grid_size - 1:
                diagonal_block_index = (current_row * grid_size) + col + 1
                if lake_array[diagonal_block_index] == cls.BlockState.UNICED.value:
                    diagonal_uniced_block_indices.append(diagonal_block_index)

        return diagonal_uniced_block_indices
