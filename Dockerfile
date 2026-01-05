# ----------  Dockerfile  ----------
# Ollama base image (CPU)
FROM ollama/ollama:latest

# Core packages + Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy helper scripts
COPY entrypoint.py /usr/local/bin/entrypoint.py
RUN chmod +x /usr/local/bin/entrypoint.py

EXPOSE 11434
ENTRYPOINT ["python3", "/usr/local/bin/entrypoint.py"]
