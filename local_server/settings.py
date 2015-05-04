import os.path


class Settings:
    user = 'admin'
    password = 'admin'
    debug = False
    port = 8000
    static = os.path.join(os.path.dirname(__file__), "static")
