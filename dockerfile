# 1. Usamos una imagen de Python oficial
FROM python:3.10-slim

# 2. Instalamos Google Chrome y dependencias del sistema
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates apt-transport-https \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# 3. Preparamos la carpeta de trabajo
WORKDIR /app
COPY . .

# 4. Instalamos tus librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# 5. Comando para arrancar tu bot
CMD ["python", "main.py"]
