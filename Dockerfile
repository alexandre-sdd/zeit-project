# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Store the SQLite database in a dedicated mount point by default.
ENV ZEIT_DATABASE_URL=sqlite:////data/test.db

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Prepare a persistent data directory for SQLite-backed deployments.
RUN mkdir -p /data

# Expose port 8000
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
