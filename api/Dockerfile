FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./api/

EXPOSE 80

CMD ["sh", "-c", "cd /app/api && alembic -c migrations.ini upgrade head && cd /app && uvicorn api.main:app --host 0.0.0.0 --port 80"]
