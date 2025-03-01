FROM python:3.9-slim

# Install Chrome and its dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    xvfb \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome WebDriver
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | awk -F'.' '{print $1}') \
    && CHROME_DRIVER_VERSION=$(wget -qO- https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}) \
    && wget -q https://chromedriver.storage.googleapis.com/${CHROME_DRIVER_VERSION}/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip -d /usr/local/bin \
    && rm chromedriver_linux64.zip \
    && chmod +x /usr/local/bin/chromedriver

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a script to start Xvfb and the application
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1024x768x16 &\ngunicorn -c gunicorn_config.py app:app' > /app/start.sh && \
    chmod +x /app/start.sh

# Expose port
EXPOSE 10000

# Start the application
CMD ["/app/start.sh"]
