from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer

from models.intellect import Intellect


def get_optimal_move(game_state: str):
    grid_size = int(len(game_state) ** 0.5)
    sanitized_game_state = Intellect.sanitize_game_state(game_state)
    intel = Intellect(grid_size)
    optimal_move = intel.get_optimal_move(sanitized_game_state, experimentation=0)
    intel.con.close()
    return Intellect.sanitize_move(game_state, optimal_move)


class OptimalMove(BaseHTTPRequestHandler):

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def do_HEAD(self):
        self._set_headers()

    def do_GET(self):
        self._set_headers()
        query = urlparse(self.path).query
        parsed_query = parse_qs(query)
        self.wfile.write(bytes(str(get_optimal_move(parsed_query['array'][0])), 'UTF-8'))


if __name__ == '__main__':
    server_address = ('', 5003)
    httpd = HTTPServer(server_address, OptimalMove)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
