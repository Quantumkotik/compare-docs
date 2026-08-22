FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv/docx-compare

# зависимости отдельным слоем: пересобираются только при изменении requirements.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

# приложение работает без прав root
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /srv/docx-compare
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3)"

# main.py в контейнере не нужен: он открывает браузер и сам выбирает порт.
# За обратным прокси с TLS добавьте --proxy-headers и --forwarded-allow-ips
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8080"]
