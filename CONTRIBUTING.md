# Contributing

感谢你的兴趣！欢迎提交 issue 和 PR。

## 开发环境

```bash
make dev      # 建 venv + 安装 ruff/pytest + 可编辑安装
make lint     # 提交前跑代码规范检查
make test     # 提交前跑单元测试
```

## 代码风格

- Python 遵循 PEP 8、PEP 484（全量类型标注），使用 `ruff` 检查。
- 所有模块首行加 `from __future__ import annotations`。
- 对外部命令的调用必须走 `network_console.core.shell`，禁止直接 `subprocess` + `shell=True`。

## 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档
- `test:` 测试
- `refactor:` 重构
- `chore:` 杂项

## 隐私要求

提交前请运行 `make privacy-check`，确保代码不含任何私人标识（私网 IP、个人目录路径、个人邮箱域名等）。

## PR 流程

1. 先开 issue 描述问题或想法
2. fork + 开分支
3. 提交时跑 `make lint && make test && make privacy-check`
4. 发起 PR，附上变更说明
