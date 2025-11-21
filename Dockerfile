# Base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Make start.sh executable
RUN chmod +x start.sh

# Start the app
CMD ["bash", "start.sh"]
