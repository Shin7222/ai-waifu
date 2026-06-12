
import base64
import threading
import subprocess
import sys
import webbrowser

from pathlib import Path

from flask import Flask, send_from_directory
from flask import request, jsonify

from flask_sock import Sock

from api import ask_ai


WEB_DIR = Path(__file__).parent / "web"
WINDOW_PATH = Path(__file__).parent / "avatar_window.py"

HOST = "127.0.0.1"
PORT = 5577

_clients = []
_clients_lock = threading.Lock()

_server_started = False
_window_proc = None


def _create_app():

    app = Flask(__name__, static_folder=None)

    sock = Sock(app)

    @app.route("/")
    def index():

        return send_from_directory(
            WEB_DIR,
            "index.html"
        )

    @app.route("/<path:filename>")
    def static_files(filename):

        return send_from_directory(
            WEB_DIR,
            filename
        )

    @app.route("/chat", methods=["POST"])
    def chat():

        data = request.get_json()

        user_message = data.get(
            "message",
            ""
        )

        print("USER:", user_message)

        try:

            result = ask_ai(
                user_message
            )

            print("RESULT:", result)

            if isinstance(result, dict):

                return jsonify({

                    "response":
                        result.get(
                            "text",
                            ""
                        ),

                    "emotion":
                        result.get(
                            "emotion",
                            "neutral"
                        ),

                    "talking": True
                })

            return jsonify({

                "response":
                    str(result),

                "emotion":
                    "neutral",

                "talking": True
            })

        except Exception as e:

            print(
                "CHAT ERROR:",
                e
            )

            return jsonify({

                "response":
                    f"Error: {e}",

                "emotion":
                    "error",

                "talking": False
            })

    @sock.route("/ws")
    def websocket_handler(ws):

        with _clients_lock:
            _clients.append(ws)

        try:

            while True:

                data = ws.receive()

                if data is None:
                    break

        except Exception:
            pass

        finally:

            with _clients_lock:

                if ws in _clients:
                    _clients.remove(ws)

    return app


def start_server(
    open_browser=True,
    open_desktop_window=False
):

    global _server_started
    global _window_proc

    if not _server_started:

        app = _create_app()

        def run():

            app.run(
                host=HOST,
                port=PORT,
                debug=False,
                use_reloader=False
            )

        threading.Thread(
            target=run,
            daemon=True
        ).start()

        _server_started = True

    url = f"http://{HOST}:{PORT}"

    if open_desktop_window:

        if (
            _window_proc is None
            or
            _window_proc.poll() is not None
        ):

            _window_proc = subprocess.Popen([
                sys.executable,
                str(WINDOW_PATH),
                url
            ])

    elif open_browser:

        webbrowser.open(url)

    return True


def is_running():

    return _server_started


def broadcast_audio(
    wav_bytes: bytes
):

    if not _clients:
        return

    payload = {

        "type": "speak",

        "audio_b64":
            base64.b64encode(
                wav_bytes
            ).decode("utf-8")
    }

    import json

    payload_json = json.dumps(
        payload
    )

    dead = []

    with _clients_lock:

        for ws in _clients:

            try:

                ws.send(
                    payload_json
                )

            except Exception:

                dead.append(ws)

        for ws in dead:

            if ws in _clients:
                _clients.remove(ws)


def broadcast_expression(
    name: str
):

    import json

    payload = json.dumps({

        "type":
            "expression",

        "name":
            name
    })

    with _clients_lock:

        for ws in list(_clients):

            try:

                ws.send(payload)

            except Exception:
                pass
