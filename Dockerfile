FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ONETRUTH_API_BOUNDARY_PROFILE=shared_env

WORKDIR /app

COPY . /app

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -e ".[api]"

EXPOSE 8080

CMD ["onetruth-api", "--host", "0.0.0.0", "--port", "8080", "--api-boundary-profile", "shared_env"]
