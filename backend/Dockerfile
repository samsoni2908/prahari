FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 prahari \
    && useradd --system --uid 10001 --gid prahari --home-dir /app --shell /usr/sbin/nologin prahari

COPY requirements.txt requirements.lock /app/
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock

COPY --chown=prahari:prahari app /app/app
COPY --chown=prahari:prahari alembic /app/alembic
COPY --chown=prahari:prahari alembic.ini /app/alembic.ini

USER prahari

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
