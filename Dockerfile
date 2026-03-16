FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api.py .
COPY en_bcv_parser.js .

# Expose port
EXPOSE 8000

# Run the application
# CMD ["python", "api.py"]
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "5"]