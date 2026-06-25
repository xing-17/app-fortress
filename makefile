# Makefile for FinConnect Application
APP_NAME := $(shell grep '^name' pyproject.toml | head -1 | cut -d '"' -f2)
APP_ALIA := 伽蓝
APP_VERS := $(shell grep '^version' pyproject.toml | head -1 | cut -d '"' -f2)
APP_PATH := $(abspath .)
CONDA_ENV := $(APP_NAME)
CONDA_ENV_FILE := environment.yml
DOCKER_IMAGE := $(APP_NAME):$(APP_VERS)
DOCKER_CONTAINER := $(APP_NAME)-container
DOCKER_PORT := 8100
DOCKER_LOG_MIRROR := $(APP_PATH)/logs/docker.raw.json.log
DOCKER_LOG_READABLE := $(APP_PATH)/logs/docker.readable.log
# REMOTE_HOST := root@101.132.22.26
# REMOTE_PATH := /root/workspace/app-fortress


clean: app/clean docker/clean
lint: app/lint


conda/install:
	@if ! conda env list | grep -qE "^$(CONDA_ENV)[[:space:]]"; then \
		echo "[app][$(APP_NAME)@$(APP_ALIA)] create env '$(CONDA_ENV)'"; \
		conda env create -f $(CONDA_ENV_FILE); \
	else \
		echo "[app][$(APP_NAME)@$(APP_ALIA)] update env '$(CONDA_ENV)'"; \
		conda env update -n $(CONDA_ENV) -f $(CONDA_ENV_FILE); \
	fi
	@echo "[app][$(APP_NAME)@$(APP_ALIA)] installing deps via (pyproject.toml) ..."
	@conda run -n $(CONDA_ENV) python -m pip install --upgrade pip
	@conda run -n $(CONDA_ENV) sh -c 'python -m pip install ".[dev]"'
	@echo "[app][$(APP_NAME)@$(APP_ALIA)] 'conda' environment installed ✅ "

conda/activate:
	@echo "[app][$(APP_NAME)@$(APP_ALIA)] activate conda by 'conda activate $(APP_NAME)'"

conda/deactivate:
	@echo "[app][$(APP_NAME)@$(APP_ALIA)] deactivate conda by 'conda deactivate'"

conda/remove:
	@conda env remove -n $(CONDA_ENV)
	@echo "[app][$(APP_NAME)@$(APP_ALIA)] 'conda' environment removed ✅ "

app/install:
	@pip install .
	@pip install .[dev]
	@echo "[app][$(APP_NAME)@$(APP_ALIA)] 'dependencies' installed ✅ "

app/clean:
	@rm -rf build dist *.egg-info
	@echo "[app][$(APP_NAME)@$(APP_ALIA)] 'build artifacts' cleaned ✅ "
	@rm -rf .pytest_cache
	@echo "[app][$(APP_NAME)@$(APP_ALIA)] 'pytest caches' cleaned ✅ "
	@rm -rf .ruff_cache
	@rm -rf .benchmarks
	@rm -rf logs/*.log logs/*.log.*
	@echo "[app][$(APP_NAME)@$(APP_ALIA)] 'ruff/benchmarks caches' cleaned ✅ "
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".DS_Store" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@echo "[app][$(APP_NAME)@$(APP_ALIA)] 'python caches' cleaned ✅ "
	@echo "[app][$(APP_NAME)@$(APP_ALIA)] 'logs' cleaned ✅ "

app/lint:
	@ruff format .
	@ruff check . --fix
	@ruff check .
	@echo "[app][$(APP_NAME)@$(APP_ALIA)] 'app' lint checked ✅"

memory/swapon:
	@echo "[memory] enabling swap space (4G) ..."
	@dd if=/dev/zero of=/swapfile bs=1M count=4096
	@chmod 600 /swapfile
	@mkswap /swapfile
	@swapon /swapfile
	@echo '/swapfile none swap sw 0 0' >> /etc/fstab
	@sudo sysctl vm.swappiness=10
	@echo "[memory] swap space enabled ✅"

memory/swapoff:
	@echo "[memory] disabling swap space ..."
	@swapoff /swapfile
	@rm -f /swapfile
	@sed -i '/\/swapfile/d' /etc/fstab
	@sudo sysctl vm.swappiness=60
	@echo "[memory] swap space disabled ✅"
