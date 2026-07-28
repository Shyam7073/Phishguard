.PHONY: setup lint format test

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

setup:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -r ml/requirements.txt
	$(PIP) install -r backend/requirements.txt

lint:
	$(VENV)/bin/ruff check .
	$(VENV)/bin/black --check .

format:
	$(VENV)/bin/black .

test:
	$(VENV)/bin/pytest ml/tests backend/tests
