# Usa una imagen base de Python
FROM python:3.10

# Define el directorio de trabajo
WORKDIR /app

# Copia los archivos del backend
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV FLASK_APP=app.py
ENV FLASK_ENV=development