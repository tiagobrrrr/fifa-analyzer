FROM python:3.12-slim

# Evita prompts do Debian
ENV DEBIAN_FRONTEND=noninteractive

# Define diretório da aplicação
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libglib2.0-0 \
    libgl1 \
    libssl-dev \
    libffi-dev \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Instalar Chrome + ChromeDriver (compatíveis com Selenium)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar pacotes Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o projeto
COPY . .

# Permitir execução
RUN chmod +x start.sh

# Comando de inicialização
CMD ["./start.sh"]
