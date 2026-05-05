.PHONY: test clean lint format dist

test:
	@PYTHONPATH=src python -m unittest discover tests/
	@zsh tests/test_cli.sh

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf test-vault dist

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

dist: clean
	uv run python -m build
	uv run twine upload dist/*
