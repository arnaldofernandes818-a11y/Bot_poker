# Usamos una imagen de Python completa
FROM python:3.10

# Instalamos Google Chrome, ChromeDriver y dependencias del sistema
RUN apt-get update && apt-get install -y wget gnupg unzip && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable --no-install-recommends

# Instalamos el ChromeDriver manualmente para asegurar compatibilidad
RUN wget -q "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/121.0.6167.85/linux64/chromedriver-linux64.zip" && \
    unzip chromedriver-linux64.zip && \
    mv chromedriver-linux64/chromedriver /usr/bin/chromedriver && \
    chmod +x /usr/bin/chromedriver && \
    rm -rf chromedriver-linux64.zip chromedriver-linux64

# --- ESTA ES LA PARTE CLAVE ---
# Definimos las rutas exactas que tu main.py pide mediante os.environ.get
ENV GOOGLE_CHROME_BIN=/usr/bin/google-chrome-stable
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Preparamos la carpeta de trabajo
WORKDIR /app
COPY . .

# Instalamos las librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# Comando para arrancar el bot
CMD ["python", "main.py"]
