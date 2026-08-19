FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends libmediainfo0v5 && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -r -s /bin/false appuser

WORKDIR /app
ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x start.sh && chown -R appuser:appuser /app

USER appuser

CMD ["./start.sh"]
