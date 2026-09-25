FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    git \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Instalar Terraform (opcional - para provisionamiento real)
RUN wget -O terraform.zip https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_linux_amd64.zip \
    && unzip terraform.zip \
    && mv terraform /usr/local/bin/ \
    && rm terraform.zip

# Copiar requirements primero
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .
# Copiar llm_client.py compartido (desde la raíz)
COPY llm_client.py .
# Exponer puerto
EXPOSE 8004

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Comando para iniciar el servicio
CMD ["uvicorn", "executor:app", "--host", "0.0.0.0", "--port", "8004"]