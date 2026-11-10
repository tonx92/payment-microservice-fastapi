# Описание 
Микросервис безопасной обработки платежей на FastApi

## Быстрый старт
Запуск
```
docker compose -f 'docker-compose.yml' up -d
```
Остановка
```
docker compose -f 'docker-compose.yml' down 
```
## Команды для тестирования

1) создание платежа POST /api/v1/payments
```
curl -X POST http://localhost:80/api/v1/payments -H "X-API-Key: change-me-to-a-secure-key" -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440003" -H "Content-Type: application/json" -d "{\"amount\": 100.50, \"currency\": \"RUB\", \"description\": \"Test payment\", \"webhook_url\": \"http://localhost:8025/webhook\", \"metadata\": {\"order_id\": \"12345\", \"source\": \"test\"}}"
```
2) получение платежа GET /api/v1/payments/{payment_id}
```
curl http://localhost:80/api/v1/payments/c86a3621-637c-45e5-a418-204ad0b49632 -H "X-API-Key: change-me-to-a-secure-key"
```
3) для получения списка таблиц в бд
```
docker exec -it $(docker compose ps -q postgres) psql -U postgres -d payments -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
```
4) для получения содержимого таблицы outbox последние 50
```
docker exec -it $(docker compose ps -q postgres) psql -U postgres -d payments -c "SELECT * FROM outbox ORDER BY id DESC LIMIT 50;"
```
5) для получения содержимого таблицы payments последние 50
```
docker exec -it $(docker compose ps -q postgres) psql -U postgres -d payments -c "SELECT * FROM payments ORDER BY id DESC LIMIT 50;"
```
6) для получения содержимого таблицы миграций последние 50
```
docker exec -it $(docker compose ps -q postgres) psql -U postgres -d payments -c "SELECT * FROM alembic_version;"
```
## Стек
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 (асинхронный режим)
- PostgreSQL
- RabbitMQ (FastStream)
- Alembic (миграции)
- Docker + docker-compose