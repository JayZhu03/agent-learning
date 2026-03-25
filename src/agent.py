"""
Agent 核心模块

实现 ReAct 循环：Thought → Action → Observation
"""

import re
from typing import Tuple, Optional
from .provider import LLMProvider
from .tools import Tools
from .prompts import get_system_prompt
from .config import Config


class CodingAgent:
    """
    编程助手 Agent
    
    实现 ReAct 模式：
    1. Thought（思考）：分析当前情况，决定下一步
    2. Action（行动）：调用工具执行操作
    3. Observation（观察）：获取执行结果
    4. 循环直到任务完成，输出 Final Answer
    """
    
    def __init__(self, work_directory: str = "."):
        """
        初始化 Agent
        
        Args:
            work_directory: 工作目录
        """
        # 初始化 LLM 提供者
        self.provider = LLMProvider(
            api_key=Config.API_KEY,
            base_url=Config.BASE_URL,
            model=Config.MODEL
        )
        
        # 初始化工具集
        self.tools = Tools(work_directory)
        
        # 工作目录
        self.work_directory = work_directory
        
        # 对话历史
        self.messages = []
    
    def run(self, user_input: str) -> str:
        """
        运行 Agent，处理用户输入
        
        Args:
            user_input: 用户的任务描述
        
        Returns:
            最终答案
        """
        # 生成系统提示
        system_prompt = get_system_prompt(
            tool_list=self.tools.get_tool_description(),
            work_directory=self.work_directory
        )
        
        # 初始化消息列表
        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"<question>{user_input}</question>"}
        ]
        
        print(f"\n{'='*50}")
        print(f"任务：{user_input}")
        print(f"{'='*50}\n")
        
        # ReAct 循环
        step = 0
        while step < Config.MAX_STEPS:
            step += 1
            print(f"--- 步骤 {step} ---")
            
            # 调用 LLM
            response = self.provider.chat(self.messages)
            
            # 添加到消息历史
            self.messages.append({"role": "assistant", "content": response})
            
            # 解析响应
            thought = self._extract_thought(response)
            action = self._extract_action(response)
            final_answer = self._extract_final_answer(response)
            
            # 打印思考
            if thought:
                print(f"\n💭 思考：{thought}")
            
            # 检查是否完成
            if final_answer:
                print(f"\n✅ 最终答案：{final_answer}\n")
                return final_answer
            
            # 检查是否有 Action
            if not action:
                print("\n❌ 错误：模型未输出有效的 Action")
                return "错误：模型未输出有效的 Action"
            
            # 解析并执行 Action
            tool_name, args = self._parse_action(action)
            
            args_display = ', '.join(repr(a)[:30] + ('...' if len(repr(a)) > 30 else '') for a in args) if args else ''
            print(f"\n🔧 执行：{tool_name}({args_display})")
            
            # 执行工具
            observation = self.tools.execute(tool_name, *args)
            
            print(f"\n🔍 观察结果：{observation[:500]}{'...' if len(observation) > 500 else ''}")
            
            # 添加观察结果到消息
            obs_message = f"<observation>{observation}</observation>"
            self.messages.append({"role": "user", "content": obs_message})
        
        # 超过最大步数
        return f"已达到最大步数限制（{Config.MAX_STEPS}），任务未完成"
    
    def _extract_thought(self, text: str) -> Optional[str]:
        """提取 <thought> 标签内容"""
        match = re.search(r"<thought>(.*?)</thought>", text, re.DOTALL)
        return match.group(1).strip() if match else None
    
    def _extract_action(self, text: str) -> Optional[str]:
        """提取 <action> 标签内容"""
        match = re.search(r"<action>(.*?)</action>", text, re.DOTALL)
        return match.group(1).strip() if match else None
    
    def _extract_final_answer(self, text: str) -> Optional[str]:
        """提取 <final_answer> 标签内容"""
        match = re.search(r"<final_answer>(.*?)</final_answer>", text, re.DOTALL)
        return match.group(1).strip() if match else None
    
    def _parse_action(self, action: str) -> Tuple[str, tuple]:
        """
        解析 Action 字符串
        
        Args:
            action: Action 字符串，格式为 "tool_name(arg1, arg2, ...)"
        
        Returns:
            (工具名, 参数元组)
        """
        # 匹配 工具名(所有内容) 的模式
        match = re.match(r"(\w+)\((.*)\)$", action, re.DOTALL)
        
        if not match:
            # 尝试更宽松的匹配
            match = re.match(r"(\w+)\((.*)\)", action, re.DOTALL)
            if not match:
                return ("unknown", ())
        
        tool_name = match.group(1)
        args_str = match.group(2).strip()
        
        # 如果没有参数
        if not args_str:
            return (tool_name, ())
        
        # === 特殊处理每个工具 ===
        
        # run_command: 整个内容就是一个命令字符串
        if tool_name == "run_command":
            cmd = self._extract_string_arg(args_str)
            return (tool_name, (cmd,))
        
        # list_files: 整个内容就是一个目录字符串
        if tool_name == "list_files":
            directory = self._extract_string_arg(args_str)
            return (tool_name, (directory,) if directory else ())
        
        # read_file: 整个内容就是一个文件路径
        if tool_name == "read_file":
            file_path = self._extract_string_arg(args_str)
            return (tool_name, (file_path,))
        
        # write_file: 需要两个参数 - 文件路径和内容
        if tool_name == "write_file":
            file_path, content = self._parse_write_file_args(args_str)
            return (tool_name, (file_path, content))
        
        # 默认处理
        return (tool_name, (args_str,))
    
    def _extract_string_arg(self, s: str) -> str:
        """
        从参数字符串中提取单个字符串参数
        处理引号包围的情况
        
        Args:
            s: 参数字符串
        
        Returns:
            提取的字符串
        """
        s = s.strip()
        
        # 如果以引号开始
        if s.startswith('"') or s.startswith("'"):
            quote = s[0]
            # 找到匹配的结束引号
            for i in range(1, len(s)):
                if s[i] == quote and (i == 0 or s[i-1] != '\\'):
                    return s[1:i]
            # 没找到结束引号，返回去掉首引号的内容
            return s[1:]
        
        # 没有引号，返回整个字符串
        return s
    
    def _parse_write_file_args(self, args_str: str) -> Tuple[str, str]:
        """
        解析 write_file 的参数
        格式: file_path, content
        content 可能包含逗号、引号、换行等
        
        Args:
            args_str: 参数字符串
        
        Returns:
            (文件路径, 内容)
        """
        args_str = args_str.strip()
        
        # 情况1: 第一个参数用引号包围
        if args_str.startswith('"') or args_str.startswith("'"):
            quote = args_str[0]
            # 找到第一个参数的结束引号
            end_quote = -1
            for i in range(1, len(args_str)):
                if args_str[i] == quote and args_str[i-1] != '\\':
                    end_quote = i
                    break
            
            if end_quote > 0:
                file_path = args_str[1:end_quote]
                # 找到逗号分隔符
                rest = args_str[end_quote+1:].strip()
                if rest.startswith(','):
                    content = rest[1:].strip()
                    # 去掉内容的首尾引号
                    content = self._extract_string_arg(content)
                    # 处理转义字符
                    content = self._unescape(content)
                    return (file_path, content)
        
        # 情况2: 没有引号，按第一个逗号分割
        comma_pos = args_str.find(',')
        if comma_pos > 0:
            file_path = args_str[:comma_pos].strip()
            content = args_str[comma_pos+1:].strip()
            content = self._extract_string_arg(content)
            content = self._unescape(content)
            return (file_path, content)
        
        # 情况3: 只有一个参数
        return (self._extract_string_arg(args_str), "")
    
    def _unescape(self, s: str) -> str:
        """
        处理转义字符
        
        Args:
            s: 包含转义字符的字符串
        
        Returns:
            处理后的字符串
        """
        return s.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')