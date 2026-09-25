FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para cachear mejor)
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .
# Copiar llm_client.py compartido (desde la raíz)
COPY llm_client.py .
# Crear directorio para logs
RUN mkdir -p /var/log

# Exponer puerto
EXPOSE 8001

# Variables de entorno por defecto
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Comando para iniciar el servicio
CMD ["uvicorn", "guardian_api:app", "--host", "0.0.0.0", "--port", "8001"]