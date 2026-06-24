help:
	cat Makefile

run:
	docker compose up

test:
	docker compose run --rm --entrypoint='pytest' app

shell:
	docker compose run --rm app shell

migrate:
	docker compose run --rm app migrate
