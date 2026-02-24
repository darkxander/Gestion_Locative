"""Entry point pour lancer Gestion Locative."""

import socket
import threading
import webbrowser
import time

from gestion_locative.app import create_app, init_db


def _find_free_port(start=5000, end=5100):
    """Trouve un port libre en commençant par 5000."""
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return start


def _open_browser(port):
    """Ouvre le navigateur après un court délai."""
    time.sleep(1.5)
    webbrowser.open(f'http://127.0.0.1:{port}')


def main():
    """Lance l'application Gestion Locative."""
    port = _find_free_port()
    app = create_app()
    init_db(app)

    print()
    print("=" * 50)
    print("  GESTION LOCATIVE")
    print("=" * 50)
    print()
    print(f"  → http://127.0.0.1:{port}")
    print()
    print("  Ctrl+C pour arrêter")
    print("=" * 50)
    print()

    threading.Thread(target=_open_browser, args=(port,), daemon=True).start()
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
