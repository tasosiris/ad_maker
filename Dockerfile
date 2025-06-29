# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Set environment variables from config.yaml (this is illustrative)
# In a real setup, manage secrets securely (e.g., using Docker secrets or cloud provider's secret management)
# For this example, we assume env vars are set manually or via docker-compose
ENV PYTHONPATH=/app

# Command to run the application
# This will be the entry point for the container
CMD ["python", "main.py", "run-full-pipeline"] 