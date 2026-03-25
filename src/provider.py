"""
Provider 模块

负责与大语言模型 API 交互
封装 OpenAI SDK，兼容阿里百炼 API
"""

from openai import OpenAI
from typing import List, Dict, Optional


class LLMProvider:
    """
    LLM 提供者
    
    封装 OpenAI SDK，支持阿里百炼等兼容 OpenAI 接口的服务
    """
    
    def __init__(self, api_key: str, base_url: str, model: str):
        """
        初始化 LLM 提供者
        
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
    
    def chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7
    ) -> str:
        """
        发送对话请求
        
        Args:
            messages: 消息列表，格式为 [{"role": "user/assistant/system", "content": "..."}]
            temperature: 温度参数，控制随机性（0-1）
        
        Returns:
            模型的回复文本
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"API 调用错误：{str(e)}"
    
    def chat_with_system(
        self, 
        system_prompt: str, 
        user_message: str,
        temperature: float = 0.7
    ) -> str:
        """
        带系统提示的对话
        
        Args:
            system_prompt: 系统提示
            user_message: 用户消息
            temperature: 温度参数
        
        Returns:
            模型的回复文本
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        return self.chat(messages, temperature)