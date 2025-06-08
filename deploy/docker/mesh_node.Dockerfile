FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose WebSocket port
EXPOSE 8765

# Run the mesh node service
CMD ["python", "-m", "deploy.mesh.mesh_interface"]
