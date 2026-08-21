"""Точка входа: поднимает сервер и открывает веб-интерфейс в браузере."""

import socket
import threading
import webbrowser

import uvicorn

from app.server import app

HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def find_free_port(host: str, preferred: int) -> int:
    """Возвращает preferred, если порт свободен, иначе любой свободный."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, preferred))
            return preferred
        except OSError:
            pass

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def open_browser_when_ready(url: str, host: str, port: int, timeout: float = 10.0) -> None:
    """Ждёт, пока сервер начнёт принимать соединения, и открывает браузер."""
    deadline = threading.TIMEOUT_MAX if timeout is None else timeout
    step = 0.1
    waited = 0.0

    while waited < deadline:
        try:
            with socket.create_connection((host, port), timeout=step):
                webbrowser.open(url)
                return
        except OSError:
            threading.Event().wait(step)
            waited += step


def main() -> None:
    port = find_free_port(HOST, DEFAULT_PORT)
    url = f"http://{HOST}:{port}"

    print(f"compare-docs запущен: {url}")
    threading.Thread(
        target=open_browser_when_ready,
        args=(url, HOST, port),
        daemon=True,
    ).start()

    uvicorn.run(app, host=HOST, port=port, log_level="info")


if __name__ == "__main__":
    main()
