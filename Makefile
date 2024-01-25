build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

reset:
	docker compose down --volumes --remove-orphans

ps:
	docker compose ps

logs:
	docker compose logs -f

revision:
	docker compose up -d server
	docker compose exec server /bin/bash -c "cd /db && alembic revision --autogenerate -m '${NAME}'"

migrate:
	docker compose up -d server
	docker compose exec server /bin/bash -c "cd /db && alembic upgrade head"

init:
	cp envs/bot.env.example envs/bot.env
	cp envs/db.env.example envs/db.env
	cp envs/sentry.env.example envs/sentry.env
	cp envs/server.env.example envs/server.env

install-local-requirements:
	find . -name requirements.txt -exec pip install -r {} \;
