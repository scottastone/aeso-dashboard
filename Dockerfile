# Use an official Python runtime as a parent image
FROM python:3.13-slim

WORKDIR /app

COPY app.py .
COPY api.key .
COPY templates/ .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Export port 2376 (AESO) and start the app.
EXPOSE 2376
CMD ["gunicorn", "--bind", "0.0.0.0:2376", "app:app"]
