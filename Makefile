.PHONY: install dev lint test build docker-build clean

install:
	pip install .

dev:
	pip install -e ".[dev]"

lint:
	ruff check k8s_investigate/
	ruff format --check k8s_investigate/

format:
	ruff check --fix k8s_investigate/
	ruff format k8s_investigate/

test:
	PYTHONWARNINGS=ignore::SyntaxWarning pytest tests/ -v

build:
	python -m build

docker-build:
	docker build -t k8s-investigate:latest .

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
