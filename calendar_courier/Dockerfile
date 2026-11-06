FROM ghcr.io/home-assistant/base:latest
LABEL org.opencontainers.image.title="Calendar Courier" org.opencontainers.image.source="https://github.com/Flushbug/ha-calendar-courier"

# lxml from Alpine so nothing needs to be compiled on any architecture
RUN apk add --no-cache python3 py3-lxml

COPY requirements.txt /app/requirements.txt
RUN python3 -m venv --system-site-packages /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

COPY calendar_courier.py /app/calendar_courier.py

CMD ["/opt/venv/bin/python3", "-u", "/app/calendar_courier.py"]
