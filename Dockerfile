# Use Python 3.12
FROM python:3.12-slim

# Workdir
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Permissions for start.sh
RUN chmod +x start.sh

EXPOSE 5000

CMD ["bash", "start.sh"]
