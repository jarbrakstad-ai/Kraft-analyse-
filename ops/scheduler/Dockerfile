FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ingest/requirements.txt ./ingest-requirements.txt
COPY backend/requirements.txt ./backend-requirements.txt
RUN pip install --no-cache-dir -r ingest-requirements.txt -r backend-requirements.txt

COPY ingest ./ingest
COPY backend/app ./backend/app

COPY ops/scheduler/crontab /etc/cron.d/kraft-analyse
RUN chmod 0644 /etc/cron.d/kraft-analyse && crontab /etc/cron.d/kraft-analyse

COPY ops/scheduler/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
