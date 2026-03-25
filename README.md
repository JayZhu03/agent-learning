# Coding Agent

一个极简的 AI Agent，用来学习 Agent 开发。

## 背景

想理解 Agent 的原理，所以从零写了一个。

主要学习：
- Agent 架构设计
- ReAct 模式
- LLM 调用
- 工具系统
- Prompt 设计

## 项目结构

```
coding-agent/
├── src/
│   ├── main.py       # 入口
│   ├── agent.py      # Agent 核心
│   ├── provider.py   # LLM 调用
│   ├── tools.py      # 工具函数
│   ├── prompts.py    # Prompt 模板
│   └── config.py     # 配置管理
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
用户输入 → System Prompt → LLM → 解析 Action → 执行工具 → 返回结果 → 继续循环
```

## 工具

| 工具 | 功能 |
|------|------|
| `read_file` | 读文件 |
| `write_file` | 写文件 |
| `run_command` | 执行命令 |
| `list_files` | 列出文件 |

## 使用方法

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入 API Key

# 运行
python src/main.py
```

## 踩坑记录

| 问题 | 原因 | 解决 |
|------|------|------|
| requirements.txt 编码错误 | 中文注释 + Windows GBK | 改纯英文 |
| 参数解析错误 | LLM 输出格式不稳定 | 每个工具单独解析 |
| 危险命令误判 | 字符串匹配 | 正则单词边界 |
| 交互程序卡住 | 等待输入 | 不适合 run_command |

## 待实现

- 结构化记忆
- Skill 模块
- 权限系统
- 更多工具
- LSP 集成

## 参考

- [OpenCode](https://github.com/anomalyco/opencode)
- [VideoCode](https://github.com/MarkTechStation/VideoCode)
- [ReAct 论文](https://arxiv.org/abs/2210.03629)

## License

MIT