# --- base image (from your registry)
ARG REGISTRY=registry.fpna.ir/fpna/common
ARG PY_IMAGE=python:3.11-slim
FROM ${REGISTRY}/${PY_IMAGE}

# Basic, predictable runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy app
COPY . .

# Collect static at build-time (skip repeating it at runtime)
RUN mkdir -p /app/staticfiles \
 && python manage.py collectstatic --noinput

EXPOSE 8000
# Migrate once at startup; static already collected in image
CMD ["sh","-c","python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"]
