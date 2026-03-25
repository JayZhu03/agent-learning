# Coding Agent MVP

> 一个极简的 AI 编程助手，用于学习 Agent 开发原理。

## 项目背景

这是一个从零开始构建的 Coding Agent MVP，用于学习：

- Agent 架构设计
- ReAct 模式实现
- LLM API 调用
- 工具系统设计
- Prompt 工程

## 架构

```
coding-agent/
├── src/
│   ├── main.py       # 入口（CLI）
│   ├── agent.py      # Agent 核心（ReAct 循环）
│   ├── provider.py   # LLM 调用封装
│   ├── tools.py      # 工具函数
│   ├── prompts.py    # Prompt 模板
│   └── config.py     # 配置管理
├── requirements.txt
├── .env              # API 配置（不提交）
└── README.md
```

## 核心概念

### ReAct 模式

```
Thought（思考）→ Action（行动）→ Observation（观察）→ 循环 → Final Answer
```

### 数据流

```
用户输入 → System Prompt + 工具描述 → LLM → 解析 Action → 执行工具 → 返回 Observation → 循环
```

## 功能

| 工具 | 功能 |
|------|------|
| `read_file` | 读取文件 |
| `write_file` | 写入文件 |
| `run_command` | 执行命令 |
| `list_files` | 列出文件 |

## 快速开始

### 1. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API

复制 `.env.example` 为 `.env`，填入你的 API Key：

```env
DASHSCOPE_API_KEY=your-api-key
DASHSCOPE_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
DASHSCOPE_MODEL=qwen3.5-plus
```

### 4. 运行

```bash
# 交互模式
python src/main.py

# 单次任务
python src/main.py -t "创建一个 hello.py 文件"
```

## 开发过程

### Day 1 - MVP 开发

**完成**：
- ✅ 项目结构搭建
- ✅ LLM 调用封装（兼容 OpenAI 接口）
- ✅ 工具系统（读/写/执行）
- ✅ ReAct 循环
- ✅ CLI 入口

**踩坑记录**：

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| requirements.txt 编码错误 | 中文注释，Windows GBK | 改纯英文 |
| 参数解析错误 | LLM 输出格式不稳定 | 重写解析逻辑，每个工具特殊处理 |
| 危险命令误判 | 字符串包含匹配 | 正则单词边界匹配 |
| 交互程序卡住 | run_command 超时 | 不适合交互程序 |

### 待实现

- [ ] 结构化记忆（文件/命令元数据）
- [ ] Skill 模块（动态加载）
- [ ] 权限系统（allow/ask/deny）
- [ ] 更多工具（grep/glob/websearch）
- [ ] LSP 集成（代码诊断）

## 学习资源

### 参考资料

- [OpenCode](https://github.com/anomalyco/opencode) - 生产级 Coding Agent
- [VideoCode](https://github.com/MarkTechStation/VideoCode) - 教学向 ReAct Agent
- [ReAct 论文](https://arxiv.org/abs/2210.03629) - Reasoning + Acting

### 相关概念

| 概念 | 说明 |
|------|------|
| **ReAct** | Reasoning + Acting，边想边做 |
| **MCP** | Model Context Protocol，工具协议 |
| **Provider** | LLM API 封装层 |
| **Skill** | 可复用的能力模块 |

## License

MIT

---

> 本项目用于学习 Agent 开发，不用于生产环境。