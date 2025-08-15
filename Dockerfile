FROM python:3.12-slim
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi
COPY . .
ENV PYTHONUNBUFFERED=1 TZ=Europe/Amsterdam
EXPOSE 8000
CMD bash -lc "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port "
