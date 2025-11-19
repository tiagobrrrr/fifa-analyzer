FROM python:3.12-slim

# Evita prompts interativos
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências de sistema necessárias para Pandas, lxml, Selenium, etc.
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libxml2-dev \
    libxslt-dev \
    libz-dev \
    curl \
    unzip \
    chromium-driver \
    chromium \
    && apt-get clean

# Criar diretório da app
WORKDIR /app

# Copiar requirements primeiro
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copiar restante dos arquivos
COPY . .

# Tornar o start.sh executável
RUN chmod +x start.sh

# Comando padrão
CMD ["./start.sh"]
