# Use an official Python runtime as a parent image
FROM python:3.11-slim
WORKDIR /app
COPY webui/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY webui/backend/. .
COPY alternator /app/alternator
EXPOSE 5000
CMD ["python3", "app.py"]
