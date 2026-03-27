# Coding Agent v1.3 测试用例

## 环境准备

```bash
# 解压并进入目录
unzip coding-agent-v1.3.zip
cd coding-agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置 API Key（编辑 .env）
```

---

## 测试用例

### 1. 基础对话（不调用工具）

```bash
python -m src.main run -t "你好"
python -m src.main run -t "什么是 Flask？"
```

**预期**: 直接返回 `<final_answer>`，无工具调用

---

### 2. 文件操作

```bash
# 创建文件
python -m src.main run -t "创建一个 hello.py，内容是 print('Hello, World!')"

# 读取文件
python -m src.main run -t "读取 hello.py"

# 编辑文件
python -m src.main run -t "把 hello.py 里的 World 改成 Agent"

# 搜索文件
python -m src.main run -t "找出所有 .py 文件"

# 搜索代码内容
python -m src.main run -t "搜索所有 print 语句"

# 创建目录
python -m src.main run -t "创建目录 test_dir"

# 删除文件
python -m src.main run -t "删除 hello.py"
```

---

### 3. Git 操作

```bash
python -m src.main run -t "查看 Git 状态"
python -m src.main run -t "查看最近 5 条提交日志"
python -m src.main run -t "查看当前差异"
```

---

### 4. HTTP 请求

```bash
python -m src.main run -t "请求 https://httpbin.org/get"
python -m src.main run -t "POST 请求 https://httpbin.org/post，数据 {\"name\": \"test\"}"
```

---

### 5. 记忆系统

```bash
python -m src.main run -t "记住这个项目使用 Python 3.10"
python -m src.main run -t "记住作者叫 jayzhu"
python -m src.main run -t "我之前让你记住什么了？"
python -m src.main run -t "列出所有记忆"
```

---

### 6. 用户交互确认

```bash
python -m src.main run -t "删除所有临时文件"
```

**预期**: 触发 `ask_user`，等待用户确认

---

### 7. 网络搜索

```bash
python -m src.main run -t "搜索 Python FastAPI 教程"
python -m src.main run -t "搜索如何用 Flask 创建 REST API"
```

---

### 8. 环境变量

```bash
python -m src.main run -t "查看 PATH 环境变量"
python -m src.main run -t "列出所有环境变量"
```

---

### 9. 命令执行

```bash
python -m src.main run -t "执行 ls -la"
python -m src.main run -t "执行 pip list"
```

---

### 10. 复杂任务（多步骤）

```bash
python -m src.main run -t "创建一个 utils.py 文件，包含一个 add 函数，然后创建 test_utils.py 测试它"
```

**预期**: 多步执行 → write_file × 2 → 完成提示

---

## 预期结果检查

| 测试 | 检查点 |
|-----|--------|
| 创建文件 | 文件存在，内容正确 |
| 读取文件 | 显示文件内容 |
| 编辑文件 | 内容已替换 |
| 搜索代码 | 显示匹配行 |
| Git 状态 | 显示分支和更改 |
| 记忆保存 | `.agent_memory.json` 存在 |
| 网络搜索 | 返回搜索结果 |
| 危险操作 | 触发 `ask_user` 确认 |

---

## 常见问题排查

| 问题 | 检查 |
|-----|------|
| API 错误 | `.env` 中 `DASHSCOPE_API_KEY` 是否正确 |
| 权限错误 | 检查 `.agent/permissions.json` |
| 找不到模块 | 确认虚拟环境已激活 |
| 命令超时 | 默认 60 秒，可在 tools.py 调整 |