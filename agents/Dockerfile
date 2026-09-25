FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .
# Copiar llm_client.py compartido (desde la raíz)
COPY llm_client.py .
# Exponer puerto
EXPOSE 8005

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV AGENT_DOMAIN=Generic
ENV AGENT_PORT=8005
ENV LOG_LEVEL=INFO

# Comando para iniciar el servicio
CMD ["python", "-m", "uvicorn", "agent_api:app", "--host", "0.0.0.0", "--port", "8005"]