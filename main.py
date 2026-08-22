"""Точка входа: поднимает сервер и открывает веб-интерфейс в браузере."""

import logging
import os
import socket
import sys
import threading
import webbrowser

import uvicorn

from app.logging_setup import LOG_FILE, setup_logging

setup_logging()
log = logging.getLogger("app.main")

from app.server import app  # noqa: E402  — импорт после настройки логирования

HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def find_free_port(host: str, preferred: int) -> int:
    """Возвращает preferred, если порт свободен, иначе любой свободный."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, preferred))
            log.debug("Порт %d свободен", preferred)
            return preferred
        except OSError as exc:
            log.warning("Порт %d занят (%s) — подбираем свободный", preferred, exc.strerror)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        port = sock.getsockname()[1]

    log.info("Выбран свободный порт %d", port)
    return port


def open_browser_when_ready(url: str, host: str, port: int, timeout: float = 10.0) -> None:
    """Ждёт, пока сервер начнёт принимать соединения, и открывает браузер."""
    step = 0.1
    waited = 0.0

    log.debug("Ждём готовности сервера на %s:%d", host, port)

    while waited < timeout:
        try:
            with socket.create_connection((host, port), timeout=step):
                log.info("Сервер готов за %.1f с — открываем браузер: %s", waited, url)
                if not webbrowser.open(url):
                    log.warning("Не удалось открыть браузер, откройте вручную: %s", url)
                return
        except OSError:
            threading.Event().wait(step)
            waited += step

    log.warning("Сервер не ответил за %.0f с — браузер не открыт, зайдите вручную: %s", timeout, url)


def main() -> None:
    log.info("Запуск compare-docs, Python %s", sys.version.split()[0])
    log.info("Логи пишутся в %s", LOG_FILE)

    # PORT задан явно — используем его как есть; иначе подбираем свободный
    env_port = os.environ.get("PORT")
    if env_port:
        port = int(env_port)
        log.info("Порт взят из переменной окружения PORT: %d", port)
    else:
        port = find_free_port(HOST, DEFAULT_PORT)

    url = f"http://{HOST}:{port}"
    log.info("compare-docs запущен: %s", url)

    threading.Thread(
        target=open_browser_when_ready,
        args=(url, HOST, port),
        daemon=True,
    ).start()

    try:
        # log_config=None — uvicorn не перебивает наши обработчики
        uvicorn.run(app, host=HOST, port=port, log_config=None)
    except KeyboardInterrupt:
        log.info("Остановлено пользователем")


if __name__ == "__main__":
    main()
