FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade pip && python -m pip install .

USER app

CMD ["celery", "-A", "jobs.celery_app", "worker", "--loglevel=INFO", "--pool=solo"]
