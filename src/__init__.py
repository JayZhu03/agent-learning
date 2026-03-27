"""
Coding Agent 包 v1.3

一个功能丰富的 AI 编程助手，基于 ReAct 模式实现。

新增功能：
- 18 个工具（文件、Git、HTTP、记忆、搜索）
- 会话恢复
- 用户交互确认
- 网络搜索
"""

from .config import Config
from .provider import LLMProvider
from .tools import Tools
from .agent import CodingAgent

__version__ = "1.3.0"

__all__ = ["Config", "LLMProvider", "Tools", "CodingAgent", "__version__"]