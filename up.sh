cd swarm_v1.0

# 1. Configurar variables de entorno
cp .env.example .env
nano .env  # Agregar OPENAI_API_KEY

# 2. Dar permisos a scripts
chmod +x scripts/*.sh

# 3. Construir todas las imágenes
docker compose build

# 4. Iniciar todos los servicios
docker compose up -d

# 5. Verificar salud
make health

# 6. Abrir dashboard
open http://localhost:8501