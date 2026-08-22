"""Настройка логирования: консоль + ротируемый файл, id запроса в каждой строке."""

import logging
import logging.handlers
import os
import sys
import time
from contextvars import ContextVar
from pathlib import Path

# Короткий идентификатор текущего запроса — попадает в каждую строку лога,
# поэтому шаги обработки одного запроса легко выделить среди параллельных.
request_id: ContextVar[str] = ContextVar("request_id", default="-")

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "compare-docs.log"

LOG_FORMAT = "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)-18s %(message)s"
DATE_FORMAT = "%H:%M:%S"

_configured = False


class RequestIdFilter(logging.Filter):
    """Подставляет id текущего запроса в запись лога."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


def setup_logging(level: str | None = None) -> None:
    """Настраивает корневой логгер. Уровень задаётся через LOG_LEVEL."""
    global _configured
    if _configured:
        return

    level_name = (level or os.environ.get("LOG_LEVEL") or "INFO").upper()
    resolved = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    id_filter = RequestIdFilter()

    # Консоль. На Windows по умолчанию cp1251 — принудительно переводим в UTF-8,
    # иначе кириллица в логах превращается в мусор.
    stream = sys.stdout
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

    console = logging.StreamHandler(stream)
    console.setFormatter(formatter)
    console.addFilter(id_filter)

    handlers: list[logging.Handler] = [console]

    LOG_DIR.mkdir(exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(id_filter)
    handlers.append(file_handler)

    root = logging.getLogger()
    root.setLevel(resolved)
    for handler in handlers:
        root.addHandler(handler)

    # uvicorn ставит свои обработчики — снимаем их, чтобы записи шли
    # через корневой логгер и попадали в файл в едином формате
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    # Сторонние библиотеки шумят на DEBUG (особенно разбор multipart) —
    # держим их на WARNING, чтобы не тонуть в чужих записях
    for name in ("python_multipart", "multipart", "httpx", "httpcore", "watchfiles", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)

    _configured = True
    logging.getLogger("app.logging").info(
        "Логирование настроено: уровень %s, файл %s", level_name, LOG_FILE
    )


class Step:
    """Контекстный менеджер: замеряет шаг и пишет его начало и конец."""

    def __init__(self, logger: logging.Logger, name: str, **context):
        self.logger = logger
        self.name = name
        self.context = context
        self.started = 0.0

    def __enter__(self) -> "Step":
        self.started = time.perf_counter()
        details = _format_context(self.context)
        self.logger.debug("→ %s%s", self.name, details)
        return self

    def add(self, **context) -> None:
        """Добавляет данные, которые попадут в строку о завершении шага."""
        self.context.update(context)

    def __exit__(self, exc_type, exc, tb) -> bool:
        elapsed = (time.perf_counter() - self.started) * 1000
        details = _format_context(self.context)
        if exc_type is None:
            self.logger.info("✓ %s за %.1f мс%s", self.name, elapsed, details)
        else:
            self.logger.error(
                "✗ %s прервано за %.1f мс%s: %s", self.name, elapsed, details, exc
            )
        return False


def _format_context(context: dict) -> str:
    if not context:
        return ""
    return " — " + ", ".join(f"{k}={v}" for k, v in context.items())
