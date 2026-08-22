"""Точка входа: поднимает веб-сервер и открывает 1111111интерфейс в браузере."""

from __future__ import annotations

import os
import socket
import threading
import time
import webbrowser

import uvicorn

HOST = os.getenv("HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("PORT", "8080"))


def pick_port(host: str, preferred: int) -> int:
    """Возвращает свободный порт: сначала пробует preferred, иначе просит порт у ОС."""
    for candidate in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, candidate))
            except OSError:
                continue
            return sock.getsockname()[1]
    raise RuntimeError("Не удалось найти свободный порт")


def main() -> None:
    port = pick_port(HOST, DEFAULT_PORT)
    url = f"http://{HOST}:{port}"

    if port != DEFAULT_PORT:
        print(f"Порт {DEFAULT_PORT} занят, используется {port}")

    print(f"Веб-интерфейс: {url}  (Ctrl+C — остановить)")

    # уникальный адрес на каждый запуск: браузер не подставит страницу из кеша
    свежий = f"{url}/?v={int(time.time())}"
    threading.Timer(1.0, lambda: webbrowser.open(свежий)).start()
    uvicorn.run("app.server:app", host=HOST, port=port, log_level="info")


if __name__ == "__main__":
    main()
