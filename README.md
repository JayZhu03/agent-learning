# Coding Agent

一个极简的 AI Agent，用来学习 Agent 开发。

**版本：1.1.1**

## 背景

想理解 Agent 的原理，边写边学，边学边写。

主要学习：
- Agent 架构设计
- ReAct 模式
- LLM 调用
- 工具系统
- Prompt 设计
- 权限系统
- 记忆系统

## 项目结构

```
coding-agent/
├── src/
│   ├── main.py         # CLI 入口
│   ├── agent.py        # Agent 核心（ReAct 循环）
│   ├── provider.py     # LLM 调用封装
│   ├── tools.py        # 工具函数
│   ├── prompts.py      # Prompt 模板
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

### 工具系统

| 工具 | 功能 |
|------|------|
| `read_file` | 读文件 |
| `write_file` | 写文件 |
| `run_command` | 执行命令 |
| `list_files` | 列出文件 |

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
# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入 API Key

# 初始化项目
python -m src.main init

# 交互模式
python -m src.main run

# 单次任务
python -m src.main run -t "创建一个 hello.py 文件"

# 指定工作目录
python -m src.main run -d /path/to/project

# 查看记忆
python -m src.main memory

# 查看权限
python -m src.main perms
```

### 交互模式命令

- `/memory` - 查看记忆报告
- `/reset` - 清空记忆
- `/note <内容>` - 添加笔记

## 踩坑记录

| 问题 | 原因 | 解决 |
|------|------|------|
| requirements.txt 编码错误 | 中文注释 + Windows GBK | 改纯英文 |
| 参数解析错误 | LLM 输出格式不稳定 | 每个工具单独解析 |
| 危险命令误判 | 字符串匹配 | 正则单词边界 |
| 交互程序卡住 | 等待输入 | 不适合 run_command |

## 架构参考

- [OpenCode](https://github.com/anomalyco/opencode) - 记忆系统、会话设计
- [Claude Code](https://claude.ai/code) - 权限系统
- [ReAct 论文](https://arxiv.org/abs/2210.03629) - 核心模式

## License

MIT