[English](SECURITY-HYGIENE.md) | [**简体中文**](SECURITY-HYGIENE.zh-CN.md)

# 安全卫生自查清单（Security Hygiene）

本工具会展示你的**真实网络标识**。截图、贴 issue、贴聊天、录屏之前，先过一遍这个清单。

## 哪些数据算敏感

| 类型 | 例子 | 为什么敏感 |
|---|---|---|
| SSID（Wi-Fi 名称） | 家里的路由器名、带人名/地址的热点 | 能反查地址、人名，甚至你的家庭住址 |
| BSSID | 路由器 MAC 地址 | 唯一标识一台物理设备，可被定位 |
| MAC 地址 | 网卡、其他设备 MAC | 唯一标识硬件，可跨网络追踪 |
| 内网 IP | 192.168.x.x、10.x.x.x、Tailscale 100.x | 暴露你的内部网络结构、设备数量 |
| 历史 Wi-Fi 列表 | 连过的所有网络名 | 相当于你的移动轨迹（住过哪些酒店、去过哪些地方） |
| 设备名 | 手机/电脑的主机名、家人设备名 | 暴露真实姓名、设备型号、家庭成员 |
| 公网 IP | 你的出口 IP | 可精确定位到城市/运营商 |
| 进程/端口 | 运行的服务、监听端口 | 暴露你装了哪些软件、开了哪些服务 |

## 分享前必做

1. **截图前**：先开「隐私模式」，或手动遮掉 SSID/BSSID/MAC/内网 IP。
2. **贴命令行输出前**：`system_profiler`、`ifconfig`、`lsof`、`networksetup -listpreferredwirelessnetworks` 的输出里几乎全是敏感数据，逐行检查。
3. **贴 git diff / commit 前**：`git diff` 里若出现上面任何一类，先替换成占位符（`user`、`10.0.0.1`、`TestNetwork`）。
4. **commit message 里也一样**：commit message 是公开历史，写真实 IP/名字 = 二次泄漏。本项目已发生过一次（见 [INCIDENT-2026-10-04](docs/INCIDENT-2026-10-04.md)）。

## 自查命令

```bash
# 扫源码 + 测试 + 文档（文件内容）
make privacy-check

# 再扫 git 全历史 commit message
make privacy-check-history
```

提交前跑一遍，两个都绿再 push。

## 核心原则

**「只是给 AI 看 / 只是给朋友看 / 只是临时贴一下」都不构成例外。** 对话记录可能留存、可能被训练、可能被误转发。敏感数据一旦离开你的本机，就无法收回。

工具（privacy-check）能挡住文件和 git 历史，但挡不住你截图和贴聊天。**人的习惯是比工具更弱的一环。**
