# Slim base image for Python 3.11
FROM python:3.11-slim

# Set working directory to /app
WORKDIR /app

# Prevent Python from writing pyc files to disc and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies if any (none for now)

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000
EXPOSE 8000

# Run uvicorn server
# --host 0.0.0.0 is crucial for Docker networking
# --port 8000 matches EXPOSE
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
