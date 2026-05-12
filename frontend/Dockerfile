# Frontend Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all application code and requirements
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "app/main.py", "--server.port", "8501", "--server.address", "0.0.0.0"]