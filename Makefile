PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: run dev lint test privacy-check clean

## 启动（直接跑，无需 venv）
run:
	$(PYTHON) -m network_console

## 建 venv 并安装 dev 依赖（ruff + pytest + 可编辑安装）
dev:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"

## 代码规范检查
lint:
	$(BIN)/ruff check src tests

## 单元测试
test:
	$(BIN)/python -m pytest

## 隐私自查（中性正则，检查源码是否残留私网IP/个人路径）
privacy-check:
	bash scripts/privacy_check.sh

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
