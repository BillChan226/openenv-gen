FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn requests pydantic
COPY openenv_adapter ./openenv_adapter
EXPOSE 8080
CMD ["uvicorn", "openenv_adapter.server.app:app", "--host", "0.0.0.0", "--port", "8080"]
