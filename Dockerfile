# ---- Base Python Image ----
FROM python:3.12-slim

# ---- Set env ----
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ---- Install system deps ----
RUN apt-get update && apt-get install -y \
    curl wget unzip chromium chromium-driver build-essential \
    && rm -rf /var/lib/apt/lists/*

# ---- Set working dir ----
WORKDIR /app

# ---- Copy requirements ----
COPY requirements.txt .

# ---- Install Python deps ----
RUN pip install --no-cache-dir -r requirements.txt

# ---- Create folder for SQLite ----
RUN mkdir -p /app/data && chmod -R 777 /app/data

# ---- Copy project ----
COPY . .

# ---- Permission for start.sh ----
RUN chmod +x start.sh

# ---- Expose port ----
EXPOSE 5000

# ---- Start ----
CMD ["./start.sh"]
