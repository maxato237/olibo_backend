FROM python:3.12-slim

WORKDIR /app

# System deps required by Playwright's Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Browsers stored inside /app so they're baked into the image layer
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright-browsers

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

COPY . .

EXPOSE 8000

CMD ["gunicorn", "olibo:create_app()", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120"]
