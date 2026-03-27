# Coding Agent

一个功能丰富的 AI Agent，用来学习 Agent 开发。

**版本：1.3**

## 背景

想理解 Agent 的原理，边写边学，边学边写。

主要学习：
- Agent 架构设计
- ReAct 模式
- LLM 调用
- 工具系统（18 个工具）
- Prompt 设计
- 权限系统
- 记忆系统

## 项目结构

```
coding-agent/
├── src/
│   ├── main.py         # CLI 入口
│   ├── agent.py        # Agent 核心（ReAct 循环 + 会话恢复）
│   ├── provider.py     # LLM 调用封装
│   ├── tools.py        # 工具函数（v1.3 18个工具）
│   ├── prompts.py      # Prompt 模板（v1.3 8个示例）
│   ├── config.py       # 配置管理
│   ├── permissions.py  # 权限系统
│   └── memory.py       # 记忆系统
├── requirements.txt
├── .env.example
└── README.md
```

## 核心概念

### ReAct 模式

思考 → 行动 → 观察 → 循环，直到完成任务。

```
Thought → Action → Observation → 循环 → Final Answer
```

### 数据流

```
用户输入 → 记忆上下文 → System Prompt → LLM → 解析 Action → 权限检查 → 执行工具 → 记录记忆 → 返回结果
```

## 功能特性

### 工具系统（v1.3 共 18 个工具）

#### 文件操作
| 工具 | 功能 |
|------|------|
| `read_file` | 读取文件（支持行范围） |
| `write_file` | 写入文件 |
| `edit_file` | 编辑文件（替换/插入/删除） |
| `delete_file` | 删除文件或空目录 |
| `list_files` | 列出目录内容 |
| `find_files` | 按模式查找文件 |
| `search_code` | 搜索代码内容 |
| `mkdir` | 创建目录 |

#### 命令执行
| 工具 | 功能 |
|------|------|
| `run_command` | 执行终端命令（带安全检查） |

#### Git 操作
| 工具 | 功能 |
|------|------|
| `git_status` | 查看状态 |
| `git_diff` | 查看差异 |
| `git_log` | 查看日志 |

#### HTTP 请求
| 工具 | 功能 |
|------|------|
| `http_get` | GET 请求 |
| `http_post` | POST 请求 |

#### 其他
| 工具 | 功能 |
|------|------|
| `get_env` | 获取环境变量（自动脱敏） |
| `memory_save/load/list` | Agent 记忆系统 |
| `ask_user` | 向用户提问确认 |
| `web_search` | 网络搜索（DuckDuckGo） |

### 权限系统

三级权限：`allow` / `ask` / `deny`

```json
{
  "tools": {
    "read_file": "allow",
    "write_file": "ask",
    "run_command": "ask"
  },
  "commands": {
    "ls*": "allow",
    "git*": "allow",
    "rm*": "deny",
    "sudo*": "deny"
  },
  "paths": {
    ".env": "deny",
    "*.key": "deny"
  }
}
```

### 记忆系统

- **会话隔离**：每次运行 = 新会话
- **跨会话持久化**：重要文件、笔记、技术栈
- **记忆文件**：`.agent/memory.json`

```json
{
  "project": { "name": "my-project" },
  "sessions": [...],
  "current_session": {...},
  "context": {
    "key_files": ["app.py"],
    "notes": ["使用 Flask"],
    "tech_stack": ["Flask", "SQLite"]
  }
}
```

## 使用方法

```bash
# 1. 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate       # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env 填入 DASHSCOPE_API_KEY

# 4. 初始化项目（可选）
python -m src.main init

# 5. 启动 Agent
python -m src.main run
```

### CLI 命令

```bash
# 交互模式
python -m src.main run

# 单次任务
python -m src.main run -t "搜索所有 TODO 注释"

# 指定工作目录
python -m src.main run -d /path/to/project

# 恢复中断的会话
python -m src.main run --resume

# 查看会话列表
python -m src.main sessions

# 查看记忆
python -m src.main memory

# 查看权限
python -m src.main perms

# 查看版本
python -m src.main -v
```

### 交互模式命令

- `/memory` - 查看记忆报告
- `/reset` - 清空记忆
- `/note <内容>` - 添加笔记

## v1.3 更新日志

### 新增工具（14 个）
- `edit_file` - 精确编辑文件
- `delete_file` - 删除文件
- `find_files` - 查找文件
- `search_code` - 搜索代码
- `mkdir` - 创建目录
- `git_status/diff/log` - Git 操作
- `http_get/post` - HTTP 请求
- `get_env` - 环境变量
- `memory_save/load/list` - Agent 记忆
- `ask_user` - 用户确认
- `web_search` - 网络搜索

### 改进
- 参数解析支持字典、布尔、数字等复杂类型
- Prompt 新增 8 个示例（v1.2 只有 4 个）
- 安全升级：正则 `\b` 单词边界匹配

## 踩坑记录

| 问题 | 原因 | 解决 |
|------|------|------|
| requirements.txt 编码错误 | 中文注释 + Windows GBK | 改纯英文 |
| 参数解析错误 | LLM 输出格式不稳定 | 每个工具单独解析 |
| 危险命令误判 | 字符串匹配 | 正则单词边界 |
| 交互程序卡住 | 等待输入 | 不适合 run_command |
| repr() 转义错误 | `\U`、`\N` 序列 | 用 str() 替代 |

## 架构参考

- [OpenCode](https://github.com/anomalyco/opencode) - 记忆系统、会话设计
- [Claude Code](https://claude.ai/code) - 权限系统
- [ReAct 论文](https://arxiv.org/abs/2210.03629) - 核心模式

## License

MIT