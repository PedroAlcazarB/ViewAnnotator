# Usa una imagen base de Python
FROM python:3.10

# Instalar dependencias del sistema necesarias para OpenCV y ultralytics
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libgtk-3-0 \
    libgl1 \
    libgthread-2.0-0 \
    libqt5gui5 \
    libqt5core5a \
    libqt5widgets5 \
    fonts-liberation \
    libglib2.0-dev \
    libfontconfig1 \
    libxss1 \
    && rm -rf /var/lib/apt/lists/*

# Define el directorio de trabajo
WORKDIR /app

# Copia los archivos del backend
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV FLASK_APP=app.py
# Crear directorios necesarios
RUN mkdir -p /app/datasets /app/ai_models

# Exponer puerto
EXPOSE 5000

# Comando de inicio para producción con Gunicorn
# Nota: solo 1 worker para mantener el modelo en memoria por proceso
# --access-logfile - : logs de acceso a stdout
# --error-logfile - : logs de error a stderr  
# --log-level info : nivel de log
CMD ["gunicorn", "--workers=1", "--threads=2", "--timeout=120", "--bind=0.0.0.0:5000", "app:app"]