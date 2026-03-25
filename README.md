# Coding Agent

从零开始写的一个极简 Agent，用来学习 Agent 开发。

## 为什么做这个

想弄懂 Agent 到底怎么工作的，就自己写了一个。

学到的东西：
- Agent 架构
- ReAct 模式
- LLM API 调用
- 工具系统
- Prompt 写法

## 项目结构

```
coding-agent/
├── src/
│   ├── main.py       # 入口
│   ├── agent.py      # Agent 核心
│   ├── provider.py   # LLM 调用
│   ├── tools.py      # 工具
│   ├── prompts.py    # Prompt
│   └── config.py     # 配置
├── requirements.txt
├── .env.example
└── README.md
```

## 核心概念

### ReAct 模式

想一步 → 做一步 → 看结果 → 继续想，循环直到完成。

```
Thought → Action → Observation → 循环 → Final Answer
```

### 数据流

```
用户输入 → Prompt + 工具列表 → LLM → 解析要做什么 → 执行 → 返回结果 → 继续
```

## 功能

| 工具 | 干什么 |
|------|--------|
| `read_file` | 读文件 |
| `write_file` | 写文件 |
| `run_command` | 跑命令 |
| `list_files` | 列文件 |

## 怎么用

### 1. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```

### 2. 装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API

复制 `.env.example` 为 `.env`，填 API Key：

```env
DASHSCOPE_API_KEY=你的key
DASHSCOPE_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
DASHSCOPE_MODEL=qwen3.5-plus
```

### 4. 跑起来

```bash
# 交互模式
python src/main.py

# 单次任务
python src/main.py -t "创建 hello.py"
```

## 踩过的坑

| 问题 | 原因 | 怎么解决的 |
|------|------|-----------|
| requirements.txt 报错 | 中文注释，Windows 编码问题 | 改成纯英文 |
| 参数解析老出错 | LLM 输出格式不稳定 | 每个工具单独写解析逻辑 |
| Add-Content 被拦截 | 匹配到 "dd" | 用正则单词边界匹配 |
| 跑游戏卡死 | 交互程序不退出 | 这种程序不适合用 run_command |

## 还想做的

- [ ] 记忆系统
- [ ] Skill 模块
- [ ] 权限系统
- [ ] 更多工具
- [ ] LSP 集成

## 参考

- [OpenCode](https://github.com/anomalyco/opencode)
- [VideoCode](https://github.com/MarkTechStation/VideoCode)
- [ReAct 论文](https://arxiv.org/abs/2210.03629)

---

学习记录，不用于生产。