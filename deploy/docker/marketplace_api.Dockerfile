FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the marketplace API server
CMD ["uvicorn", "marketplace.api.marketplace_api:app", "--host", "0.0.0.0", "--port", "8000"]
