# Описание 
Микросервис безопасной обработки платежей на FastApi

## Быстрый старт
Запуск
```
compose -f 'docker-compose.yml' up -d --build
```
```
compose -f compose --file 'docker-compose.yml' down 
```
## Команды тестирования

## Стек
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 (асинхронный режим)
- PostgreSQL
- RabbitMQ (FastStream)
- Alembic (миграции)
- Docker + docker-compose