FROM python:3.14-slim

WORKDIR /app

# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (the .env file is never baked in; pass the API key
# at runtime with: docker run --env-file .env -it ...)
COPY . .

# Write incident data to a volume so records survive container restarts
VOLUME ["/app/data"]

EXPOSE 5000

CMD ["sh", "-c", "python -m flask --app app init-db && exec python app.py"]
