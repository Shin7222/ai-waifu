"""
avatar_server.py — Local web server untuk menampilkan avatar Live2D.

Menyajikan halaman web/index.html + model Live2D, dan menyediakan
WebSocket /ws untuk mengirim event ke browser (misalnya audio TTS
untuk lip-sync).

Dijalankan di thread terpisah dari main.py — tidak blocking CLI.
Avatar bisa dibuka sebagai:
  - tab browser biasa (open_browser=True)
  - window desktop standalone via pywebview (open_desktop_window=True)
"""

import base64
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

try:
    from flask import Flask, send_from_directory
    from flask_sock import Sock
except ImportError:
    Flask = None  # ditangani di start_server()

WEB_DIR     = Path(__file__).parent / "web"
WINDOW_PATH = Path(__file__).parent / "avatar_window.py"
HOST        = "127.0.0.1"
PORT        = 5577

_clients = []          # list of websocket connections
_clients_lock = threading.Lock()
_server_started = False
_window_proc = None    # subprocess pywebview yang sedang berjalan


def _create_app():
    app  = Flask(__name__, static_folder=None)
    sock = Sock(app)

    @app.route("/")
    def index():
        index_path = WEB_DIR / "index.html"
        if not index_path.exists():
            return (
                f"<h1>404 - index.html tidak ditemukan</h1>"
                f"<p>WEB_DIR: {WEB_DIR}</p>"
                f"<p>Pastikan folder 'web/' ada di sebelah avatar_server.py</p>",
                404,
            )
        return send_from_directory(WEB_DIR, "index.html")

    @app.route("/<path:filename>")
    def static_files(filename):
        return send_from_directory(WEB_DIR, filename)

    @sock.route("/ws")
    def ws_handler(ws):
        with _clients_lock:
            _clients.append(ws)
        try:
            while True:
                # Kita tidak butuh pesan dari browser, tapi recv() perlu
                # dipanggil untuk mendeteksi koneksi putus.
                data = ws.receive()
                if data is None:
                    break
        finally:
            with _clients_lock:
                if ws in _clients:
                    _clients.remove(ws)

    return app


def start_server(open_browser: bool = True, open_desktop_window: bool = False) -> bool:
    """Mulai server avatar di thread terpisah.
    - open_browser=True       → buka tab browser default
    - open_desktop_window=True → buka window desktop standalone (pywebview)
    Return True jika server berhasil dijalankan/sudah berjalan.
    """
    global _server_started, _window_proc

    if Flask is None:
        return False

    if not _server_started:
        app = _create_app()

        def run():
            app.run(host=HOST, port=PORT, debug=False, use_reloader=False)

        t = threading.Thread(target=run, daemon=True)
        t.start()
        _server_started = True

    url = f"http://{HOST}:{PORT}"

    if open_desktop_window:
        # Jalankan sebagai subprocess agar pywebview punya main thread sendiri
        if _window_proc is not None and _window_proc.poll() is None:
            return True  # window sudah terbuka
        try:
            _window_proc = subprocess.Popen([sys.executable, str(WINDOW_PATH), url])
        except Exception as e:
            print(f"❌ Gagal membuka window avatar: {e}")
            print("   Pastikan pywebview terinstall: pip install pywebview --break-system-packages")
            return False
    elif open_browser:
        webbrowser.open(url)

    return True


def is_running() -> bool:
    return _server_started


def broadcast_audio(wav_bytes: bytes):
    """Kirim audio WAV ke semua browser yang terhubung untuk diputar + lip-sync."""
    if not _clients:
        return
    b64 = base64.b64encode(wav_bytes).decode("ascii")
    payload = '{"type":"speak","audio_b64":"' + b64 + '"}'
    with _clients_lock:
        dead = []
        for ws in _clients:
            try:
                ws.send(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _clients.remove(ws)


def broadcast_expression(name: str):
    """Trigger expression Live2D di browser (opsional)."""
    if not _clients:
        return
    payload = '{"type":"expression","name":"' + name + '"}'
    with _clients_lock:
        for ws in list(_clients):
            try:
                ws.send(payload)
            except Exception:
                pass