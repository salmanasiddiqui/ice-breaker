from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer

from models.intellect import Intellect


class OptimalMove(BaseHTTPRequestHandler):

    def _get_optimal_move(self, game_state: str):
        sanitized_game_state = Intellect.sanitize_game_state(game_state)
        grid_size = int(len(game_state) ** 0.5)
        with Intellect.get_db_conn(grid_size) as con:
            log_msg, optimal_move = Intellect.get_optimal_move(con, sanitized_game_state, experimentation=0)
        con.close()
        sanitized_move = Intellect.sanitize_move(game_state, optimal_move)
        self.log_message('%s - %s (%s) - %s', sanitized_game_state, optimal_move, log_msg, sanitized_move)
        return sanitized_move

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
        self.wfile.write(bytes(str(self._get_optimal_move(parsed_query['array'][0])), 'UTF-8'))


if __name__ == '__main__':
    server_address = ('', 5003)
    httpd = HTTPServer(server_address, OptimalMove)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
