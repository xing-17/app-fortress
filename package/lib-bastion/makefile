# PyPI package name (from pyproject.toml)
PKG_NAME := $(shell grep '^name' pyproject.toml | head -1 | cut -d '"' -f2)
PKG_ALIAS := 翁城
PKG_VERS := $(shell grep '^version' pyproject.toml | head -1 | cut -d '"' -f2)
PKG_PATH := $(abspath .)

.PHONY: help version deps clean lint test setup all install build upload zip
setup: install
all: install test lint clean build setup

# ========== Library General ==========
help:
	@echo
	@echo "$(PKG_NAME) ($(PKG_ALIAS)) Make targets:"
	@echo "  version           Show current version"
	@echo "  install           Install library and dependencies (pip install .[dev])"
	@echo "  clean             Clean build artifacts and caches"
	@echo "  test              Run tests (pytest -q)"
	@echo "  lint              Ruff checks and fixes (non-destructive)"
	@echo "  build             Build sdist/wheel (python -m build)"
	@echo "  setup             Install library in editable mode"
	@echo "  zip               Zip repo (exclude caches/build)"
	@echo

version:
	@echo "[$(PKG_NAME)@$(PKG_ALIAS)] Current version:" $(PKG_VERS)

# ========== Library Executions ==========

install:
	@pip install .
	@pip install .[dev]
	@echo "[$(PKG_NAME)@$(PKG_ALIAS)] 'dependencies' installed ✅ "

clean:
	@rm -rf build dist *.egg-info
	@echo "[$(PKG_NAME)@$(PKG_ALIAS)] 'build artifacts' cleaned ✅ "

	@rm -rf .pytest_cache
	@echo "[$(PKG_NAME)@$(PKG_ALIAS)] 'pytest caches' cleaned ✅ "

	@rm -rf .ruff_cache
	@rm -rf .benchmarks
	@echo "[$(PKG_NAME)@$(PKG_ALIAS)] 'ruff/benchmarks caches' cleaned ✅ "

	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".DS_Store" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@echo "[$(PKG_NAME)@$(PKG_ALIAS)] 'python caches' cleaned ✅ "

test:
	pytest -q
	@echo "[$(PKG_NAME)@$(PKG_ALIAS)] 'library' tests passed ✅ "

lint:
	@ruff format .
	@ruff check . --fix
	@ruff check .
	@echo "[$(PKG_NAME)@$(PKG_ALIAS)] 'library' lint checked ✅"

build:
	@python -m build
	@twine check dist/*
	@echo "[$(PKG_NAME)@$(PKG_ALIAS)] 'library' built OK ✅"

setup:
	@pip install -e .
	@echo "[$(PKG_NAME)@$(PKG_ALIAS)] 'library' setup in editable mode OK ✅"

upload:
	@twine upload dist/*
	@echo "[$(PKG_NAME)@$(PKG_ALIAS)] 'library' uploaded to PyPI ✅"

zip:
	@zip -r "$(PKG_NAME)-$$(date +%Y%m%d).zip" . \
		-x "*.git*" \
		-x "*.DS_Store" \
		-x "__pycache__/*" \
		-x "*.pyc" \
		-x "*.pyo" \
		-x ".pytest_cache/*" \
		-x ".ruff_cache/*" \
		-x "dist/*" \
		-x "build/*" \
		-x "*.egg-info/*" \
		-x "*.zip"
	@echo "[$(PKG_NAME)@$(PKG_ALIAS)] 'library' zipped ✅"
