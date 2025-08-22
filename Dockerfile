# ---------- Build stage ----------
FROM python:3.11-slim AS builder


ENV PYTHONDONTWRITEBYTECODE=1 \
PYTHONUNBUFFERED=1 \
PIP_NO_CACHE_DIR=1


WORKDIR /app


RUN apt-get update && apt-get install -y --no-install-recommends \
build-essential \
libpq-dev \
default-libmysqlclient-dev \
libjpeg-dev \
zlib1g-dev \
&& rm -rf /var/lib/apt/lists/*


COPY requirements.txt ./
RUN python -m pip install --upgrade pip && pip wheel --wheel-dir=/wheels -r requirements.txt


# ---------- Runtime stage ----------
FROM python:3.11-slim AS runtime


ENV PYTHONDONTWRITEBYTECODE=1 \
PYTHONUNBUFFERED=1


# Create non-root user
RUN useradd -m appuser
WORKDIR /app


# Only runtime libs
RUN apt-get update && apt-get install -y --no-install-recommends \
libpq5 \
default-libmysqlclient-dev \
libjpeg62-turbo \
zlib1g \
&& rm -rf /var/lib/apt/lists/*


# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-index --find-links=/wheels -r /wheels/requirements.txt || \
(echo "Generating requirements.txt from wheels" && ls /wheels | sed -n 's/^\(.*\)-[0-9].*\.whl$/\1/p' >/dev/null)
COPY requirements.txt ./
RUN python -m pip install --no-index --find-links=/wheels -r requirements.txt


# Copy project
COPY . /app


# Permissions
RUN chown -R appuser:appuser /app
USER appuser


EXPOSE 8000


# Default command (overridable)
CMD ["gunicorn", "main.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]