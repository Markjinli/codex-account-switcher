# Codex Account Switcher / Codex 账号切换器

一个跨平台工具，用于在多个 Codex CLI 账号之间一键切换。切换时会完整搬移 `~/.codex` 目录，确保每个账号的认证、配置、会话、记忆、插件、技能等全部数据独立隔离。

A cross-platform tool for switching between multiple Codex CLI accounts with one click. It swaps the entire `~/.codex` directory, keeping auth, config, sessions, memories, plugins, skills, and all other data isolated per account.

---

## GUI 版本（推荐）

```
codex-switch-gui
```

两个板块，操作直觉：

| 板块 | 功能 |
|------|------|
| **Current Account** | 显示当前登录账号，点击 `Save` 保存 |
| **Saved Profiles** | 已保存账号列表，`→` 切换 / `×` 删除 / `Add New Account` 登出 |

保存时会弹出对话框，可自定义名称（留空默认用邮箱）。

### 启动

```bash
# Windows — 双击 codex-switch-gui.bat 或在终端运行
codex-switch-gui

# Mac / Linux
python3 ~/.codex-switcher/gui/main.py
```

GUI 依赖 Flet：`pip install flet`

---

## CLI 版本

### 安装 / Installation

```bash
# 1. 克隆仓库 / Clone the repo
git clone https://github.com/Markjinli/codex-account-switcher.git ~/.codex-switcher

# 2. 加入 PATH（Windows）
powershell -ExecutionPolicy Bypass -File "%USERPROFILE%\.codex-switcher\add-to-path.ps1"

# Mac / Linux
echo 'export PATH="$HOME/.codex-switcher:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

依赖：Python 3.8+

### 用法 / Usage

```
codex-switch              查看当前账号 + 所有配置
codex-switch current      查看当前登录的账号
codex-switch list         列出所有已保存的配置
codex-switch save <名称>   保存当前登录为一份配置
codex-switch switch <名称> 切换到指定配置（自动停止 Codex）
codex-switch logout       清除登录状态
codex-switch delete <名称> 删除指定配置
codex-switch diff <名称>   对比当前与指定配置的差异
codex-switch clean         清理自动备份
```

### 典型流程 / Typical Workflow

```bash
# 登录第一个账号 → 保存
codex login
codex-switch save personal

# 登录第二个账号 → 保存
codex-switch logout
codex login
codex-switch save work

# 随时切换
codex-switch switch personal   # 切到个人账号
codex-switch switch work       # 切到工作账号
```

---

## 原理 / How It Works

```
~/.codex/           ← Codex 实际使用的目录（当前生效）
~/.codex-switcher/
  ├── codex-switch.py      ← CLI 主程序
  ├── gui/
  │   ├── main.py          ← GUI 主程序（Flet）
  │   └── core.py          ← 核心逻辑
  ├── profiles/
  │   ├── personal/        ← 完整 .codex 副本（个人账号）
  │   └── work/            ← 完整 .codex 副本（工作账号）
  └── state.json           ← 元数据
```

切换时：备份当前 `~/.codex` → 用目标 profile 覆盖 → 完成。

When switching: backs up current `~/.codex` → replaces it with the target profile → done.

---

## 注意事项 / Notes

- **切换前工具会自动停止 Codex 进程**，无需手动退出
- 支持 Windows / macOS / Linux
- profile 目录包含敏感信息（token），请勿分享
- `vendor_imports` 等缓存目录不会被复制，Codex 会自动重建

The tool auto-stops Codex before switching. Supports Windows / macOS / Linux.

---

## GitHub

https://github.com/Markjinli/codex-account-switcher

## 许可证 / License

MIT
