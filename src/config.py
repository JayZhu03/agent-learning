"""
配置模块

负责加载环境变量和提供全局配置
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Config:
    """全局配置类"""
    
    # 版本信息
    VERSION: str = "1.1.0"
    
    # 阿里百炼 API 配置
    API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    BASE_URL: str = os.getenv("DASHSCOPE_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")
    MODEL: str = os.getenv("DASHSCOPE_MODEL", "qwen3.5-plus")
    
    # Agent 配置
    MAX_STEPS: int = 20  # ReAct 最大循环次数
    WORK_DIRECTORY: str = "."  # 默认工作目录
    
    @classmethod
    def validate(cls) -> bool:
        """验证配置是否完整"""
        if not cls.API_KEY:
            print("错误：未设置 DASHSCOPE_API_KEY")
            return False
        return True