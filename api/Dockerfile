FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./api/

EXPOSE 80

CMD ["sh", "-c", "alembic -c api/migrations.ini upgrade head && uvicorn api.main:app --host 0.0.0.0 --port 80"]
