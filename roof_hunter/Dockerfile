FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port 10000 (standard for Render and some cloud providers)
EXPOSE 10000

# Set environment variables for Gunicorn
ENV GUNICORN_BIND=0.0.0.0:10000
ENV GUNICORN_WORKERS=4
ENV GUNICORN_TIMEOUT=120

# Run the application with Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:10000", "app:app"]
