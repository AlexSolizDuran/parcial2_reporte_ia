# Usamos una imagen ligera de Python 3.10
FROM python:3.10-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero el archivo de requerimientos para aprovechar la caché de Docker
COPY requirements.txt .

# Instalamos las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código (main.py, etc)
COPY . .

# Exponemos el puerto (Render usa uno dinámico, pero esto es buena práctica)
EXPOSE 8000

# Comando para ejecutar la aplicación
# Usamos 'sh -c' para poder leer la variable de entorno $PORT que Render inyecta automáticamente
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]