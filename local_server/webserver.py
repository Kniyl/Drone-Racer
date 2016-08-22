from base64 import decodestring as decode_64

from tornado import ioloop, web, websocket
from settings import Settings


last_race_setup = None
server = None
liveWebSockets = set()


class MainHandler(web.RequestHandler):
    def get(self):
        self.render("index.html")


class BasicProtectedHandler(web.RequestHandler):
    def prepare(self):
        auth_header = self.request.headers.get('Authorization')
        if auth_header is None or not auth_header.startswith('Basic '):
            self.set_status(401)
            self.set_header(
                    'WWW-Authenticate',
                    'Basic realm="Drone Racer reserved"')
            self._transforms = []
            self.finish()
            return
        user, password = decode_64(auth_header[6:].encode()).split(b':', 2)
        if (user.decode() != Settings.user or
                password.decode() != Settings.password):
            raise web.HTTPError(403)


class PostHandler(BasicProtectedHandler):
    def post(self):
        data = self.get_body_argument('data')
        server.add_callback(webSocketSendMessage, self._build_message(data))
        self.set_status(200)
        self.finish()


class SetupHandler(PostHandler):
    def _build_message(self, data):
        global last_race_setup
        last_race_setup = '{"action": "setup", ' + data[1:]
        return last_race_setup


class WarmupHandler(PostHandler):
    def _build_message(self, data):
        return '{"action": "warmup", ' + data[1:]


class UpdateHandler(PostHandler):
    def _build_message(self, data):
        return '{"action": "update", ' + data[1:]


class LeaderBoardHandler(PostHandler):
    def _build_message(self, data):
        return '{"action": "leaderboard", ' + data[1:]


class GetHandler(BasicProtectedHandler):
    def get(self):
        global last_race_setup
        last_race_setup = None
        data={'action': self._build_action()}
        server.add_callback(webSocketSendMessage, data)
        self.set_status(200)
        self.finish()


class CancelHandler(GetHandler):
    def _build_action(self):
        return 'cancel'


class FinishHandler(GetHandler):
    def _build_action(self):
        return 'finish'


class DefaultWebSocket(websocket.WebSocketHandler):
    def open(self):
        print("WebSocket opened")
        self.set_nodelay(True)
        liveWebSockets.add(self)
        if last_race_setup:
            self.write_message(last_race_setup)

    def on_message(self, message):
        print('Message incomming:', message)

    def on_close(self):
        liveWebSockets.remove(self)
        print("WebSocket closed")


def webSocketSendMessage(message):
    removable = set()
    for ws in liveWebSockets:
        if not ws.ws_connection or not ws.ws_connection.stream.socket:
            removable.add(ws)
        else:
            ws.write_message(message)
    for ws in removable:
        liveWebSockets.remove(ws)


def serve_forever():
    global server
    application = web.Application(
        [
            (r"/", MainHandler),
            (r"/setup/", SetupHandler),
            (r"/setup", SetupHandler),
            (r"/warmup/", WarmupHandler),
            (r"/warmup", WarmupHandler),
            (r"/update/", UpdateHandler),
            (r"/update", UpdateHandler),
            (r"/leaderboard/", LeaderBoardHandler),
            (r"/leaderboard", LeaderBoardHandler),
            (r"/cancel/", CancelHandler),
            (r"/cancel", CancelHandler),
            (r"/finish/", FinishHandler),
            (r"/finish", FinishHandler),
            (r"/websocket/", DefaultWebSocket),
        ],
        static_path=Settings.static,
        debug=Settings.debug,
    )
    application.listen(Settings.port)
    print('Server listening on port', Settings.port)
    server = ioloop.IOLoop.instance()
    try:
        server.start()
    except KeyboardInterrupt:
        pass
    print('Goodbye')


if __name__ == "__main__":
    serve_forever()
