FROM python:3.12-slim

ARG HURRICANE_VERSION=2.0.0rc1
ENV HURRICANE_VERSION=${HURRICANE_VERSION} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

WORKDIR /app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install --no-cache-dir "django-hurricane==${HURRICANE_VERSION}"

COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

COPY src/ /app/src/

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "manage.py", "serve", "--port", "8000"]
