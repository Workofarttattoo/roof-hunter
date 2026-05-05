# AERO-COMMAND: High-Fidelity Forensic Container
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for GIS and DB
RUN apt-get update && apt-get install -y \
    gcc \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire forensic suite
COPY . .

# Expose the Flask Port
EXPOSE 5001

# Production Environment Variables
ENV FLASK_APP=server.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5001

# Launch the AERO-COMMAND Engine
CMD ["python", "server.py"]
