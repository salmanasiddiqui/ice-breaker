# Ice-Breaker

To train a bot on a grid
```shell
python -m scripts.train 4
```
Where `4` is the size of grid

To run http server which returns optimal move for given state
```shell
python -m scripts.optimal_move_api
```
And then make GET request to `http://0.0.0.0:5003?array=1111121111111111111111111`

Where `1111121111111111111111111` is the state of game
