FROM ghcr.io/home-assistant/base:latest
LABEL org.opencontainers.image.title="Kalenderbote" org.opencontainers.image.source="https://github.com/Flushbug/ha-kalenderbote"

# lxml aus Alpine, damit auf allen Architekturen nichts kompiliert werden muss
RUN apk add --no-cache python3 py3-lxml

COPY requirements.txt /app/requirements.txt
RUN python3 -m venv --system-site-packages /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

COPY kalenderbote.py /app/kalenderbote.py

CMD ["/opt/venv/bin/python3", "-u", "/app/kalenderbote.py"]
