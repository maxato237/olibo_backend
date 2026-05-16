FROM python:3.11-slim

WORKDIR /app

# System deps required by Playwright's Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium + its OS-level dependencies at build time
# This bakes the browser into the image so it persists across restarts
RUN python -m playwright install --with-deps chromium

COPY . .

EXPOSE 8000

CMD ["gunicorn", "olibo:create_app()", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120"]
