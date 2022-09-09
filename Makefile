help:
	cat Makefile

run:
	docker-compose up

test:
	docker-compose run --rm --entrypoint='python /app/setup.py' app test

shell:
	docker-compose run --rm app shell

bash:
	docker-compose run --rm --entrypoint='/bin/bash' app

migrate:
	docker-compose run --rm app migrate
