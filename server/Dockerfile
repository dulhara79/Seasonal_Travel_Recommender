# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Ensure pip is up to date
RUN python -m pip install --upgrade pip setuptools wheel

# Copy only requirements first to leverage Docker cache
COPY requirements.txt ./requirements.txt

# Install system deps needed for some Python packages (e.g., build tools)
# Keep them minimal to reduce image size; add more if build failures require it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Expose the port the app runs on (Hugging Face Spaces expects 7860 by default)
EXPOSE 7860

# Default environment variables; user should override in production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Use port 7860 by default to be compatible with Hugging Face Spaces; allow override with $PORT
ENV PORT=7860

# Run uvicorn. Use the PORT environment variable so services like Hugging Face can override it.
CMD ["sh", "-c", "uvicorn server.api.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
