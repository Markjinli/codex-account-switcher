# Codex Account Switcher / Codex 账号切换器

一个跨平台命令行工具，用于在多个 Codex CLI 账号之间一键切换。切换时会完整搬移 `~/.codex` 目录，确保每个账号的认证、配置、会话、记忆、插件、技能等全部数据独立隔离。

A cross-platform CLI tool for switching between multiple Codex CLI accounts with one command. It swaps the entire `~/.codex` directory, keeping auth, config, sessions, memories, plugins, skills, and all other data isolated per account.

---

## 安装 / Installation

```bash
# 1. 克隆仓库 / Clone the repo
git clone https://github.com/Markjinli/codex-account-switcher.git ~/.codex-switcher

# 2. 加入 PATH（Windows 运行这个 / On Windows）
powershell -ExecutionPolicy Bypass -File "%USERPROFILE%\.codex-switcher\add-to-path.ps1"

# Mac / Linux
echo 'export PATH="$HOME/.codex-switcher:$PATH"' >> ~/.bashrc   # 或 ~/.zshrc
source ~/.bashrc
```

**依赖**：Python 3.8+（系统自带或自行安装） / Requires Python 3.8+.

---

## 用法 / Usage

```
codex-switch              查看当前账号 + 所有配置
codex-switch current      查看当前登录的账号
codex-switch list         列出所有已保存的配置
codex-switch save <名称>   保存当前登录为一份配置
codex-switch switch <名称> 切换到指定配置（自动备份当前状态）
codex-switch delete <名称> 删除指定配置
codex-switch diff <名称>   对比当前与指定配置的差异
codex-switch clean         清理自动备份，释放磁盘空间
```

### 典型流程 / Typical Workflow

```bash
# 登录第一个账号 → 保存
codex login
# ... 完成登录后 ...
codex-switch save personal

# 退出 Codex，登录第二个账号 → 保存
# Quit Codex first, then login with another account
codex login
codex-switch save work

# 以后随时切换 / Switch anytime
codex-switch switch personal   # 切到个人账号
codex-switch switch work       # 切到工作账号
```

---

## 原理 / How It Works

```
~/.codex/           ← Codex 实际使用的目录（当前生效）
~/.codex-switcher/
  ├── codex-switch.py    ← 主程序
  ├── profiles/
  │   ├── personal/      ← 完整 .codex 副本（个人账号）
  │   └── work/          ← 完整 .codex 副本（工作账号）
  └── state.json         ← 元数据
```

切换时：备份当前 `~/.codex` → 用目标 profile 覆盖 → 完成。

When switching: backs up current `~/.codex` → replaces it with the target profile → done.

每次 `switch` 前会自动创建一份带时间戳的备份，以防误操作。可用 `clean` 命令清理。

---

## 注意事项 / Notes

- **切换前请先退出 Codex**（工具会检测并提醒）
- 支持 Windows / macOS / Linux
- profile 目录包含敏感信息（token），请勿分享

**Quit Codex before switching** — the tool will detect and warn you if it's still running.

---

## 许可证 / License

MIT
