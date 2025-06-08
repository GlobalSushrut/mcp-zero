FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create an entrypoint script for the deployment service
RUN echo '#!/bin/bash\npython -m deploy.agents.deployment_manager' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Run the deployment service
CMD ["/app/entrypoint.sh"]
