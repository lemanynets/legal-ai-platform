.PHONY: install lint test typecheck

install:
	pip install -r requirements.txt

lint:
	ruff check .

test:
	pytest -x --tb=short --timeout=300 --cov=. --cov-report=term

typecheck:
	mypy . --ignore-missing-imports