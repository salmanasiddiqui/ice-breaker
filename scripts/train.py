import argparse
import timeit

from models.intellect import Intellect


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Trains the bot on given size of grid.')
    parser.add_argument('grid_size',
                        type=int,
                        choices=[4, 5, 6, 7, 8, 9],
                        help='Size of grid on which to train (min: 4, max: 9)')
    parser.add_argument('--exp',
                        type=int,
                        default=40,
                        choices=list(range(10, 101, 10)),
                        help='Percent of experimentation. Default: 40')
    args = parser.parse_args()

    def train():
        intel = Intellect(grid_size=args.grid_size)
        intel.train(experimentation=args.exp)
        intel.con.close()
    print(timeit.repeat(train, repeat=10, number=1))
