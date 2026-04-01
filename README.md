# Vitara — Full Stack MVP

Персональный подбор БАДов: анкета → рекомендации → сбор лида.

```
vitara/
├── frontend/         — HTML/CSS/JS лендинг + квиз
├── app/              — FastAPI бекенд
├── alembic/          — Миграции БД
├── nginx.conf        — Reverse proxy: / → frontend, /api/* → FastAPI
├── docker-compose.yml
└── Dockerfile
```

## Запуск (одна команда)

Требования: Docker + Docker Compose, свободный порт 80.

```bash
docker compose up --build
```

Открыть: http://localhost  
API docs: http://localhost/docs

### Применить миграции (первый запуск)

```bash
docker compose exec api alembic revision --autogenerate -m "initial"
docker compose exec api alembic upgrade head
```

В dev-режиме таблицы создаются автоматически — шаг необязателен.

## Тесты (без Docker)

```bash
pip install -r requirements.txt
pytest -v
```
