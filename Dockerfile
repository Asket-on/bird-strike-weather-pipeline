FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY pyproject.toml Makefile ./
COPY src/ ./src
COPY tests/ ./tests
COPY sql/ ./sql
COPY data/ ./data
COPY dags/ ./dags

# Install pip dependencies (if any) and pytest for testing
RUN pip install --no-cache-dir pytest

# Set Python path
ENV PYTHONPATH=/app/src

# Default command: run unit tests
CMD ["python", "-m", "unittest", "discover", "-s", "tests"]
