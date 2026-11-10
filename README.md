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
## Команды тестирования
нужны команды:
1) для получения списка таблиц в бд
```
docker exec -it $(docker compose ps -q postgres) psql -U postgres -d payments -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"

```
2) для получения содержимого таблицы outbox последние 50
```
docker exec -it $(docker compose ps -q postgres) psql -U postgres -d payments -c "SELECT * FROM outbox ORDER BY id DESC LIMIT 50;"
```
3) для получения содержимого таблицы payments последние 50
```
docker exec -it $(docker compose ps -q postgres) psql -U postgres -d payments -c "SELECT * FROM payments ORDER BY id DESC LIMIT 50;"
```
4) для получения содержимого таблицы миграций последние 50
```
docker exec -it $(docker compose ps -q postgres) psql -U postgres -d payments -c "SELECT * FROM outbox ORDER BY id DESC LIMIT 50;"
```
## Стек
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 (асинхронный режим)
- PostgreSQL
- RabbitMQ (FastStream)
- Alembic (миграции)
- Docker + docker-compose