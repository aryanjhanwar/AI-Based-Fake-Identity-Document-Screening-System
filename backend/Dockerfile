FROM python:3.11-slim

# Install system dependencies required for OpenCV and Paddle
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Set environment flags
ENV PYTHONUNBUFFERED=1 \
    FLAGS_enable_pir_api=0 \
    PORT=5000

EXPOSE 5000

# Start production WSGI server
CMD ["sh", "-c", "gunicorn server:app --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 180"]
