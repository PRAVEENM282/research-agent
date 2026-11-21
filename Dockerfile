FROM python:3.11.11-slim-bookworm AS dependencies
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt ./requirements.txt
RUN python -m pip install --prefix=/install -r requirements.txt

FROM python:3.11.11-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app LOG_DIR=/app/logs
RUN groupadd --gid 1000 handoff \
    && useradd --uid 1000 --gid handoff --create-home --shell /usr/sbin/nologin handoff \
    && mkdir -p /app/logs \
    && chown -R handoff:handoff /app
COPY --from=dependencies /install /usr/local
WORKDIR /app
COPY --chown=handoff:handoff src ./src
COPY --chown=handoff:handoff logs/.gitkeep ./logs/.gitkeep
USER handoff
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log"]
