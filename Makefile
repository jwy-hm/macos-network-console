PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: run dev lint test smoke privacy-check i18n-check clean

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

## 冒烟测试（起服务检查首页 + 静态资源全 200）
smoke:
	bash scripts/smoke.sh

## 隐私自查（私网IP/个人路径/本机用户名/邮箱，Python 实现）
privacy-check:
	$(PYTHON) scripts/privacy_check.py

## i18n 检查（除 i18n.js 外 web 前端无中文残留）
i18n-check:
	$(PYTHON) scripts/i18n_check.py

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
