FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install dependencies first (includes Flask and Werkzeug for ProxyFix)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (the .env file is never baked in; pass the API key
# at runtime with: docker run --env-file .env -it ...)
COPY . .
RUN chmod +x /app/startup.sh

# Write incident data to a volume so records survive container restarts
VOLUME ["/app/data"]

EXPOSE 5000

CMD ["sh", "-c", "export FLASK_DEBUG=false && python -m flask --app app init-db && exec python app.py"]
