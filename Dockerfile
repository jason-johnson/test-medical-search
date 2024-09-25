FROM python:3.11.10-slim-bookworm AS builder

RUN pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app
COPY app/poetry.lock app/pyproject.toml ./

RUN poetry install --no-interaction --no-root

# To enable ssh & remote debugging on app service change the base image to the one below
# FROM mcr.microsoft.com/azure-functions/python:4-python3.11-appservice
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true \
    VIRTUAL_ENV=/home/site/wwwroot/.venv \
    PATH="/home/site/wwwroot/.venv/bin:$PATH"

WORKDIR /home/site/wwwroot

COPY --from=builder /app/.venv ./.venv
COPY app/ ./