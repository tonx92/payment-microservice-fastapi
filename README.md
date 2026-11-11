# Описание 
Микросервис безопасной обработки платежей на FastApi с реализацией outbox

## Быстрый старт
1. Клонируйте рпозиторий

        git clone git@github.com:tonx92/payment-microservice-fastapi.git

2. Скопируйте файл .env.example и назовите .env (Опционально: измените параметры по умолчанию)
2. Запустите проект:

        docker compose -f 'docker-compose.yml' up -d

4. Откройте Веб интерфейс rabbitmq что бы отслеживать состояние очередей
http://localhost:15672/
5. (Опционально) Для удобство можно воспользоваться OpenAPI.json 



## Команды для тестирования (CMD)

1) создание платежа POST /api/v1/payments

        curl -X POST http://localhost:80/api/v1/payments -H "X-API-Key: change-me-to-a-secure-key" -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440003" -H "Content-Type: application/json" -d "{\"amount\": 100.50, \"currency\": \"RUB\", \"description\": \"Test payment\", \"webhook_url\": \"http://localhost:8025/webhook\", \"metadata\": {\"order_id\": \"12345\", \"source\": \"test\"}}"

    Headers:
    - `X-API-Key` — API-ключ для аутентификации
    - `Idempotency-Key` — уникальный ключ идемпотентности (max 128 символов)
    - `Content-Type` — application/json

    Body:
    - `amount` — сумма платежа (обязательный, > 0)
    - `currency` — код валюты (по умолчанию: RUB)
    - `description` — описание платежа (опционально, max 500 символов)
    - `metadata` — дополнительные метаданные (опционально, dict)
    - `webhook_url` — URL для webhook-уведомления (опционально, max 1024 символов)

2) получение платежа GET /api/v1/payments/{payment_id}

        curl http://localhost:80/api/v1/payments/c86a3621-637c-45e5-a418-204ad0b49632 -H "X-API-Key: change-me-to-a-secure-key"

    Path:
    - `payment_id` — UUID платежа (обязательный)

    Headers:
    - `X-API-Key` — API-ключ для аутентификации

3) для получения списка таблиц в бд

        docker compose exec postgres psql -U postgres -d payments -P pager=off -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"

4) для получения содержимого таблицы outbox последние 50

        docker compose exec postgres psql -U postgres -d payments -P pager=off -c "SELECT * FROM outbox ORDER BY created_at DESC LIMIT 50;"

5) для получения содержимого таблицы payments последние 50

        docker compose exec postgres psql -U postgres -d payments -P pager=off -c "SELECT * FROM payments ORDER BY created_at DESC LIMIT 50;"

6) для получения содержимого таблицы миграций последние 50

        docker compose exec postgres psql -U postgres -d payments -P pager=off -c "SELECT * FROM alembic_version;"

7) Остановка проекта

        docker compose -f 'docker-compose.yml' down 

## Стек
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 (асинхронный режим)
- PostgreSQL
- RabbitMQ (FastStream)
- Alembic (миграции)
- Docker + docker-compose