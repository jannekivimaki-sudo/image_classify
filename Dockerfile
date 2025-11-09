FROM python:3.11-slim

# Asenna ffmpeg ja muut tarpeelliset työkalut
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kopioi vaaditut tiedostot
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Tee skriptit ajettaviksi
RUN chmod +x /app/start_services.sh /app/auto_classify_service.py

ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["/app/start_services.sh"]