.PHONY: install project build publish package-install lint clean

install:
	poetry install

project:
	poetry run python main.py

build:
	poetry build

publish:
	poetry publish --dry-run

lint:
	poetry run ruff check .
