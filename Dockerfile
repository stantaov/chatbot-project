# Use the official Python image as a base
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the FastAPI app files to the container
COPY backend.py /app/
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the FastAPI port
EXPOSE 8000

# Set environment variables (ensure these are configured in the environment or passed at runtime)
# ENV KEY_VAULT_NAME=your_key_vault_name

# Command to run FastAPI using uvicorn
CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]
