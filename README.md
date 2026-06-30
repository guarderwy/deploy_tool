# 部署工具 (Deploy Tool)

> 基于 PyQt5 的 Windows 桌面代码部署工具，支持 HTML / Vue / PHP / Go / Node.js 项目一键部署到远程服务器，支持 Git 仓库与本地差异对比。

---

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [安装与运行](#安装与运行)
- [使用指南](#使用指南)
- [Git 仓库集成](#git-仓库集成)
- [安全设计](#安全设计)
- [项目结构](#项目结构)
- [测试](#测试)
- [打包为 EXE](#打包为-exe)
- [常见问题](#常见问题)
- [配置文件位置](#配置文件位置)

---

## 功能特性

### 核心部署
- **多项目类型支持** — HTML、Vue（打包后 dist/）、PHP、Go（编译后二进制）、Node.js、通用项目
- **一键部署** — 选中项目 → 对比差异 → 勾选文件 → 确认部署
- **增量同步** — 默认按文件大小+修改时间快速对比，可选 SHA256 严格模式
- **文件预览** — 部署前展示所有文件变化（新增 / 修改 / 删除），支持手动勾选和按状态过滤

### 安全管理
- **危险命令拦截** — 内置 11 类危险命令黑名单（rm -rf /、fork bomb、dd 磁盘破坏、shutdown 重启、iptables -F、curl|bash 等）
- **路径安全校验** — 禁止操作系统保护路径（/etc、/usr、/bin 等 13 个），禁止 .. 目录穿越，禁止超出项目根目录
- **配置加密** — Windows DPAPI 绑定当前用户账户，AES-GCM 加密所有服务器凭据和配置，无需输入主密码

### 服务器管理
- **多认证方式** — 密码认证 / SSH 密钥认证（支持密钥口令）
- **代理连接** — SOCKS5 / HTTP 代理 / SSH ProxyJump 跳板机，轻松连接境外服务器
- **连接池** — 按服务器复用 SSH 连接，30 秒 keepalive，10 分钟空闲自动回收
- **连接测试** — 一键测试服务器连通性

### 备份与回滚
- **部署前自动备份** — 远程 tar 打包当前文件，保留在服务器 /tmp 目录
- **一键回滚** — 从备份列表选择历史版本，确认后自动恢复
- **备份清理** — 按项目配置最大备份数自动清理旧备份

### 前后置命令
- 部署前 / 部署后自动执行自定义远程命令（如 `pm2 restart`、`systemctl reload`）
- 每条命令均经过安全检查，危险命令自动拦截

### 项目类型预设
- **HTML** — 排除 .git/、*.md，直接上传
- **Vue** — 排除 src/、node_modules/、配置文件，上传 dist/ 内容
- **PHP** — 排除 .env、vendor/、日志文件，可选修复权限
- **Go** — 排除 *.go 源码、go.mod，上传编译后二进制，可选重启服务
- **Node.js** — 排除 src/、test/、node_modules/，可选远程 npm install + 重启
- **通用** — 自由配置

### 界面
- **三栏布局** — 左侧服务器/项目树，中间项目信息与操作，右侧差异预览/部署历史
- **暗色/亮色主题** — 自动跟随 Windows 系统主题，可在设置中修改
- **实时日志** — 底部日志面板，部署过程实时输出，按天轮转存储

---

## 技术栈

| 领域 | 选型 | 说明 |
|------|------|------|
| GUI | PyQt5 5.15 | 原生桌面框架 |
| SSH/SFTP | paramiko | 纯 Python SSH 实现 |
| 代理 | PySocks | SOCKS5 代理支持 |
| 加密 | pywin32 (DPAPI) + cryptography (AES-GCM) | 企业级加密 |
| 日志 | loguru | 零配置日志 |
| 打包 | PyInstaller | 单文件 exe 分发 |
| 测试 | unittest | 标准库测试 |

---

## 安装与运行

### 环境要求
- Windows 10 / 11
- Python 3.12+（建议 3.13）

### 安装步骤

```bash
# 1. 克隆项目
cd d:\www\deploy_tool

# 2. 创建虚拟环境
"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m venv .venv

# 3. 安装依赖
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 启动

```bash
.venv\Scripts\python.exe main.py
```

首次启动自动用 Windows DPAPI 生成加密密钥，无需配置。

### 依赖列表 (requirements.txt)

```
PyQt5==5.15.11
paramiko>=3.4.0
PySocks>=1.7.1
cryptography>=42.0.0
pywin32>=306
loguru>=0.7.0
pyinstaller>=6.0.0
```

---

## 使用指南

### 1. 添加服务器

点击菜单 **服务器 → 添加服务器**，填写：

| 字段 | 说明 | 示例 |
|------|------|------|
| 服务器名称 | 自定义标识 | `生产服务器` |
| 主机 | IP 或域名 | `192.168.1.100` |
| 端口 | SSH 端口 | `22` |
| 用户名 | SSH 用户 | `deploy` |
| 认证方式 | 密码 / 密钥 | `密码` |
| 密码 | SSH 密码 | `***` |

**代理配置**（连接境外服务器时使用）：

| 代理类型 | 说明 |
|---------|------|
| 无代理 | 直连 |
| SSH 跳板 | 通过一台可访问的服务器作为跳板 |
| SOCKS5 | 通过 SOCKS5 代理 |
| HTTP | 通过 HTTP 代理 |

### 2. 添加项目

在服务器树中右键服务器 → **添加项目**，或菜单 **项目 → 添加项目**：

| 字段 | 说明 | 示例 |
|------|------|------|
| 项目名称 | 自定义标识 | `管理后台` |
| 关联服务器 | 从列表选择 | `生产服务器` |
| 项目类型 | 选择预设模板 | `Vue 前端 (打包后)` |
| 本地路径 | 本地项目目录 | `D:\projects\admin\dist` |
| 远程路径 | 服务器目标路径 | `/var/www/admin` |

选择项目类型后，排除规则和前后置命令会自动填充，可手动修改。

### 3. 部署流程

```
选择项目 → 点击「对比差异」 → 查看文件变化 → 勾选文件 → 确认部署
```

1. 左侧树选择项目
2. 点击 **对比差异** 按钮
3. 右侧「差异预览」Tab 展示所有变化的文件：
   - 🟢 新增 — 本地有，远程无
   - 🟡 修改 — 本地与远程不一致
   - 🔴 删除 — 远程有，本地无
4. 勾选需要同步的文件
5. 点击 **部署** 按钮确认

### 4. 回滚

1. 选择项目 → 点击 **回滚** 按钮
2. 从备份列表中选择要恢复的版本
3. 二次确认后自动清空并恢复文件

### 5. 排除规则

在项目配置中设置 gitignore 风格的排除规则，每行一条：

```
.git/
node_modules/
vendor/
.env
.env.*
*.log
*.pyc
__pycache__/
```

- 以 `/` 结尾的规则匹配整个目录（不限层级）
- 支持 `*` 通配符（如 `*.log`、`.env*`）

---

## Git 仓库集成

当项目本身是 Git 仓库时，工具提供两种差异对比模式：

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **本地对比** (默认) | 本地工作区 vs HEAD 提交 | 代码已 `git add` / `git commit` |
| **GitHub 对比** | 本地工作区 vs GitHub 远程仓库指定分支 | 多机协作 / 服务器侧拉取前预览 |

### 本地 Git 差异

通过 `git diff --name-status HEAD` + `git ls-files --others --exclude-standard` 实现：

- 已跟踪文件的变化（M / A / D / R / C）
- **未跟踪的新文件**（即使未 `git add` 也会被识别）
- 自动遵守 `.gitignore` 规则与项目 `exclude_patterns`

### GitHub 远程对比

通过 GitHub REST API v3 拉取远端目录树后与本地对比：

1. 在项目配置中填写 `github_repo`（如 `owner/repo`）和 `github_branch`（默认 `main`）
2. 可选：填写 GitHub Token（私有仓库必需，公有仓库可留空）— Token 会以 AES-GCM 加密存储
3. 点击「对比差异」时自动调用 GitHub API 拉取仓库目录树
4. 按路径对比本地与 GitHub 文件，输出新增 / 修改 / 删除列表

> 提示：GitHub API 未鉴权时每小时 60 次，配置 Token 后提升到 5000 次。

---

## 安全设计

### 加密方案

```
首次启动
  → 生成随机 AES-256 密钥
  → Windows DPAPI 加密（绑定当前用户账户）
  → 存储为 master.key.enc

运行时
  → DPAPI 解密 → 拿到 AES 密钥
  → AES-GCM 解密 config.enc → 加载配置
  → 运行时解密服务器密码（内存持有，退出即丢）
```

- **DPAPI**：Windows 原生加密 API，密钥绑定当前用户凭证，其他账户无法解密
- **AES-GCM**：认证加密，带 nonce + 认证标签，防篡改
- **无主密码**：无需每次输入密码，但换账户/换机器需重新配置

### 危险命令黑名单

| 类别 | 拦截内容 |
|------|---------|
| 文件破坏 | `rm -rf /`、`rm -rf /etc`、`rm -rf ~`、`rm -rf /*` |
| 系统破坏 | `dd of=/dev/sd*`、`mkfs`、`> /dev/sd*` |
| 进程破坏 | fork bomb `:(){:\|:&};:` |
| 系统操作 | `shutdown`、`reboot`、`halt`、`poweroff`、`init 0` |
| 权限破坏 | `chmod -R 777 /`、`chown -R root /` |
| 网络锁死 | `iptables -F`（防火墙清空） |
| 远程执行 | `curl \| bash`、`wget \| sh`（警告级） |

### 路径保护

禁止部署到以下系统路径：`/`、`/etc`、`/usr`、`/bin`、`/sbin`、`/boot`、`/var`、`/root`、`/home`、`/proc`、`/sys`、`/dev`、`/lib`、`/lib64`

所有上传/删除操作强制在项目 `remote_path` 范围内，禁止 `..` 目录穿越。

---

## 项目结构

```
deploy_tool/
├── main.py                          # 程序入口
├── requirements.txt                 # 依赖列表
├── build.spec                       # PyInstaller 打包配置
├── README.md                        # 本文档
├── .gitignore
│
├── src/
│   └── deploy_tool/
│       ├── app.py                   # 应用启动引导
│       ├── config/
│       │   ├── models.py            # 数据模型（6 个 dataclass）
│       │   ├── crypto.py            # DPAPI + AES-GCM 加解密
│       │   ├── store.py             # 加密配置存储与索引
│       │   ├── paths.py             # 应用数据路径
│       │   └── presets.py           # 项目类型预设（6 种）
│       ├── core/
│       │   ├── safety.py            # 危险命令拦截 + 路径校验
│       │   ├── backup.py            # tar 远程备份 + 回滚
│       │   ├── commands.py          # 带安全检查的命令执行
│       │   ├── deployer.py          # 部署编排器
│       │   ├── ssh/
│       │   │   ├── client.py        # SSH 客户端封装（双认证）
│       │   │   ├── proxy.py         # 代理工厂（SOCKS5/HTTP/ProxyJump）
│       │   │   └── pool.py          # 连接池
│       └── sync/
│           ├── differ.py        # 文件差异对比引擎（本地 ↔ 远程）
│           ├── git_differ.py    # GitHub 仓库差异对比（API 模式）
│           ├── engine.py        # 同步引擎（上传/删除/自动创目）
│           └── filters.py       # 排除规则过滤器
│       ├── ui/
│       │   ├── main_window.py       # 主窗口（三栏布局）
│       │   ├── theme.py             # 暗色/亮色主题系统
│       │   ├── dialogs/
│       │   │   ├── server_dialog.py # 服务器配置对话框
│       │   │   ├── project_dialog.py# 项目配置对话框
│       │   │   ├── deploy_dialog.py # 部署预览对话框
│       │   │   ├── rollback_dialog.py# 回滚 + 设置对话框
│       │   │   └── settings_dialog.py
│       │   ├── widgets/
│       │   │   ├── server_tree.py   # 服务器/项目树
│       │   │   ├── diff_view.py     # 差异文件预览
│       │   │   └── log_panel.py     # 日志面板
│       │   └── workers/
│       │       └── base.py          # Worker 基类 + 4 个线程
│       └── utils/
│           ├── logger.py            # loguru 配置
│           ├── hash.py              # 文件 SHA256 哈希
│           └── fs.py                # 文件系统辅助
│
└── tests/
    ├── test_crypto.py               # 加密模块测试 (7 用例)
    ├── test_safety.py               # 安全模块测试 (14 用例)
    ├── test_differ.py               # 排除规则测试 (4 用例)
    └── test_integration.py          # 全功能集成测试 (33 用例)
```

---

## 测试

### 运行所有测试

```bash
# 单元测试（25 个用例）
.venv\Scripts\python.exe -m unittest tests.test_crypto tests.test_safety tests.test_differ -v

# 集成测试（33 个用例，含 GUI）
set QT_QPA_PLATFORM=offscreen
.venv\Scripts\python.exe tests\test_integration.py
```

### 测试覆盖

| 模块 | 用例数 | 覆盖内容 |
|------|--------|---------|
| crypto | 7 | AES-GCM 加解密往返 / 防篡改 / DPAPI 往返 / 空串 / JSON 加密 / 密钥生成 |
| safety | 14 | 危险命令拦截 / 安全命令放行 / rm -rf 根路径 / fork bomb / dd / chmod / curl\|bash / shutdown / 路径保护 / .. 穿越 / 项目越界 |
| filters | 4 | 目录排除 / 文件模式 / 通配符 / 空规则 |
| integration | 33 | 配置层全流程 / 安全边界 / 排除规则 / 预设 / SSH模块 / GUI实例化 |

---

## 打包为 EXE

```bash
.venv\Scripts\python.exe -m PyInstaller build.spec
```

产物在 `dist/部署工具.exe`。

---

## 常见问题

### Q1: 本地新增了文件，「对比差异」不显示？

A: 「对比差异」默认按 **本地 vs 远程服务器** 对比，不会读取 Git 状态。如果项目本身是 Git 仓库，请使用 `Differ.compute_git_diff()`（已修复对未跟踪文件的识别）。普通模式下请确认文件已存在于本地路径且未被 `exclude_patterns` 排除。

### Q2: 提示「git diff 失败」或「未找到 git 命令」？

A: 在 Windows 上需要先安装 [Git for Windows](https://gitforwindows.org/) 并将 `git.exe` 加入 PATH。打开 `cmd` 输入 `git --version` 验证。

### Q3: 配置文件换机器后无法解密？

A: 配置使用 Windows DPAPI 加密，密钥绑定当前 Windows 用户账户。换账户或换机器后无法解密，需要手动删除 `%APPDATA%\deploy_tool\config.enc` 与 `master.key.enc` 重新配置。

### Q4: 部署到境外服务器连接超时？

A: 使用代理功能：
- **SSH 跳板**：填一台能访问目标的中转机
- **SOCKS5 / HTTP 代理**：填代理地址端口

### Q5: 危险命令被拦截但我确认要执行？

A: 工具内置的安全黑名单**不可关闭**。这是为了防止误操作破坏服务器。如确实需要执行，请手动 SSH 到服务器操作。

### Q6: 部署大文件（>100MB）卡住？

A: 当前 SFTP 走 SSH 通道，单文件过大时速度受限于 SSH 加密。推荐：
- 对大文件启用 SHA256 hash 对比以避免重复上传
- 拆分大文件，或使用 rsync 等专用工具

### Q7: 如何重置所有配置？

A: 删除整个配置目录：
```bash
rd /s /q "%APPDATA%\deploy_tool"
```
下次启动会重新生成加密配置。

### Q8: 集成测试报错「QWidget: Cannot create a QWidget without QApplication」？

A: 集成测试需要设置无头平台：
```bash
set QT_QPA_PLATFORM=offscreen
```

---

## 配置文件位置

| 文件 | 位置 | 说明 |
|------|------|------|
| 加密配置 | `%APPDATA%\deploy_tool\config.enc` | AES-GCM 加密的完整配置 |
| 主密钥 | `%APPDATA%\deploy_tool\master.key.enc` | DPAPI 加密的 AES 密钥 |
| 日志 | `%APPDATA%\deploy_tool\logs\` | 按天轮转，保留 30 天 |

即：`C:\Users\<用户名>\AppData\Roaming\deploy_tool\`
