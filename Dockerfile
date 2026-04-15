FROM python:3.11-slim

WORKDIR /app

# Install system packages required by Playwright's Chromium
# (handled via `playwright install-deps` below, but wget is needed first)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer-caching friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium browser and its OS-level dependencies.
# PLAYWRIGHT_BROWSERS_PATH puts the binaries in a fixed location so they
# are accessible regardless of which user runs the container at runtime.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application source
COPY . .

EXPOSE 5000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
