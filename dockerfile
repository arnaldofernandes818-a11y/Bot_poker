# Usamos una imagen de Python completa para evitar errores de dependencias
FROM python:3.10

# Instalamos Google Chrome de forma segura
RUN apt-get update && apt-get install -y wget gnupg && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Preparamos la carpeta de trabajo
WORKDIR /app
COPY . .

# Instalamos tus librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# Comando para arrancar el bot
CMD ["python", "main.py"]
