.PHONY: help install lint format check test clean

help: ## Show this help message
	@echo "iTunes Database Parser - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install development dependencies
	pip install -r requirements.txt
	pre-commit install

lint: ## Run ruff linter
	ruff check itunes_db_parser.py

format: ## Format code with ruff
	ruff format itunes_db_parser.py

check: ## Run all checks (lint + format)
	ruff check itunes_db_parser.py
	ruff format --check itunes_db_parser.py

test: ## Test the parser (requires iTunes database files)
	python itunes_db_parser.py --help
	@echo "Manual testing required - run with your iTunes database files"

clean: ## Clean up generated files
	rm -f *.csv
	rm -rf __pycache__/
	find . -name "*.pyc" -delete
