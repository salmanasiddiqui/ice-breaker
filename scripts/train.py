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
                        choices=list(range(0, 101, 10)),
                        help='Percent of experimentation. Default: 40')
    parser.add_argument('--minimax',
                        type=bool,
                        default=False,
                        help='To train vs minimax algo. Default: False')
    args = parser.parse_args()

    def train():
        if args.minimax:
            Intellect.train_vs_minimax(args.grid_size, experimentation=args.exp)
        else:
            Intellect.train_vs_self(args.grid_size, experimentation=args.exp)
    print(timeit.repeat(train, repeat=10, number=1))
