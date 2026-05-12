# Backend Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all application code and dependencies
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]