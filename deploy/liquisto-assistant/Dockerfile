FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements-liquisto-assistant.txt ./
RUN pip install --no-cache-dir -r requirements-liquisto-assistant.txt \
    && addgroup --system --gid 10001 runtime \
    && adduser --system --uid 10001 --ingroup runtime runtime

COPY registry/tenants/liquisto/tenant.json ./registry/tenants/liquisto/tenant.json
COPY registry/tenants/liquisto/knowledge ./registry/tenants/liquisto/knowledge
COPY src ./src

USER 10001:10001

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "src.api.liquisto_assistant_main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--log-level", "info"]
