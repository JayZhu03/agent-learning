"""
Agent 核心模块

实现 ReAct 循环：Thought → Action → Observation
支持会话恢复
"""

import re
from typing import Tuple, Optional
from .provider import LLMProvider
from .tools import Tools
from .prompts import get_system_prompt
from .config import Config
from .permissions import Permissions
from .memory import Memory, SessionStatus


class CodingAgent:
    """
    编程助手 Agent
    
    实现 ReAct 模式：
    1. Thought（思考）：分析当前情况，决定下一步
    2. Action（行动）：调用工具执行操作
    3. Observation（观察）：获取执行结果
    4. 循环直到任务完成，输出 Final Answer
    """
    
    def __init__(self, work_directory: str = ".", interactive: bool = True):
        """
        初始化 Agent
        
        Args:
            work_directory: 工作目录
            interactive: 是否交互模式（影响权限询问）
        """
        # 初始化权限系统（配置文件在 .agent/permissions.json）
        self.permissions = Permissions(work_directory=work_directory)
        
        # 初始化记忆系统（记忆文件在 .agent/memory.json）
        self.memory = Memory(work_directory=work_directory)
        
        # 初始化 LLM 提供者
        self.provider = LLMProvider(
            api_key=Config.API_KEY,
            base_url=Config.BASE_URL,
            model=Config.MODEL
        )
        
        # 初始化工具集
        self.tools = Tools(
            work_directory=work_directory,
            permissions=self.permissions,
            memory=self.memory
        )
        self.tools.set_interactive(interactive)
        
        # 工作目录
        self.work_directory = work_directory
        
        # 是否交互模式
        self.interactive = interactive
        
        # 对话历史
        self.messages = []
        
        # 是否是恢复的会话
        self.is_resumed = False
    
    def resume(self, session_id: str = None) -> bool:
        """
        恢复会话
        
        Args:
            session_id: 要恢复的会话ID（默认恢复最后一个中断的会话）
        
        Returns:
            是否成功恢复
        """
        session = self.memory.resume_session(session_id)
        if not session:
            return False
        
        self.is_resumed = True
        
        # 恢复对话历史
        self.messages = session.get("messages", [])
        
        print(f"\n🔄 已恢复会话: {session.get('id')}")
        print(f"   任务: {session.get('task', 'Unknown')}")
        print(f"   已执行: {len(session.get('commands', []))} 个命令")
        print(f"   已写入: {len(session.get('files_written', []))} 个文件")
        
        return True
    
    def run(self, user_input: str) -> str:
        """
        运行 Agent，处理用户输入
        
        Args:
            user_input: 用户的任务描述
        
        Returns:
            最终答案
        """
        # 如果不是恢复的会话，开始新会话
        if not self.is_resumed:
            self.memory.start_session(task=user_input)
        
        # 记录用户消息
        self.memory.add_message("user", user_input)
        
        # 获取记忆上下文
        memory_context = self.memory.get_summary()
        
        # 生成系统提示
        system_prompt = get_system_prompt(
            tool_list=self.tools.get_tool_description(),
            work_directory=self.work_directory,
            memory_context=memory_context
        )
        
        # 初始化或恢复消息列表
        if not self.messages:
            self.messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"<question>{user_input}</question>"}
            ]
        else:
            # 恢复的会话，添加新消息
            self.messages.append({"role": "user", "content": f"<question>{user_input}</question>"})
        
        # 重置恢复标志
        self.is_resumed = False
        
        print(f"\n{'='*50}")
        print(f"任务：{user_input}")
        print(f"{'='*50}\n")
        
        # ReAct 循环
        step = 0
        final_answer = None
        success = False
        
        while step < Config.MAX_STEPS:
            step += 1
            print(f"--- 步骤 {step} ---")
            
            # 调用 LLM
            response = self.provider.chat(self.messages)
            
            # 添加到消息历史
            self.messages.append({"role": "assistant", "content": response})
            self.memory.add_message("assistant", response)
            
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
                success = True
                break
            
            # 检查是否有 Action
            if not action:
                print("\n❌ 错误：模型未输出有效的 Action")
                final_answer = "错误：模型未输出有效的 Action"
                break
            
            # 解析并执行 Action
            try:
                tool_name, args = self._parse_action(action)
            except Exception as e:
                print(f"\n❌ 解析 Action 失败: {str(e)}")
                final_answer = f"错误：解析 Action 失败 - {str(e)}"
                break
            
            args_display = ', '.join(repr(a)[:30] + ('...' if len(repr(a)) > 30 else '') for a in args) if args else ''
            print(f"\n🔧 执行：{tool_name}({args_display})")
            
            # 执行工具（已集成权限检查和记忆记录）
            try:
                observation = self.tools.execute(tool_name, *args)
            except Exception as e:
                observation = f"工具执行错误：{str(e)}"
            
            print(f"\n🔍 观察结果：{observation[:500]}{'...' if len(observation) > 500 else ''}")
            
            # 添加观察结果到消息
            obs_message = f"<observation>{observation}</observation>"
            self.messages.append({"role": "user", "content": obs_message})
            self.memory.add_message("user", obs_message)
            
            # 定期保存（防止中断丢失）
            if step % 5 == 0:
                self.memory.save()
        
        # 结束会话
        if step >= Config.MAX_STEPS:
            final_answer = f"已达到最大步数限制（{Config.MAX_STEPS}），任务未完成"
            success = False
        
        # 生成摘要（取最终答案的前 200 字符）
        summary = final_answer[:200] if final_answer else None
        self.memory.end_session(summary=summary, success=success)
        
        # 保存记忆
        self.memory.save()
        
        return final_answer or "任务未完成"
    
    def interrupt(self):
        """
        中断当前会话（用户退出时调用）
        保存状态以便后续恢复
        """
        if self.memory.get_current_session():
            self.memory.interrupt_session()
            print("\n💾 会话已保存，可使用 --resume 恢复")
    
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
            cmd = self._extract_string_arg(args_str, normalize_path=False)
            return (tool_name, (cmd,))
        
        # list_files: 整个内容就是一个目录字符串
        if tool_name == "list_files":
            directory = self._extract_string_arg(args_str, normalize_path=True)
            return (tool_name, (directory,) if directory else ())
        
        # read_file: 整个内容就是一个文件路径
        if tool_name == "read_file":
            file_path = self._extract_string_arg(args_str, normalize_path=True)
            return (tool_name, (file_path,))
        
        # write_file: 需要两个参数 - 文件路径和内容
        if tool_name == "write_file":
            file_path, content = self._parse_write_file_args(args_str)
            return (tool_name, (file_path, content))
        
        # 默认处理
        return (tool_name, (args_str,))
    
    def _extract_string_arg(self, s: str, normalize_path: bool = False) -> str:
        """
        从参数字符串中提取单个字符串参数
        处理引号包围的情况
        
        Args:
            s: 参数字符串
            normalize_path: 是否规范化路径（Windows 反斜杠转正斜杠）
        
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
                    result = s[1:i]
                    if normalize_path:
                        result = result.replace('\\', '/')
                    return result
            # 没找到结束引号，返回去掉首引号的内容
            result = s[1:]
            if normalize_path:
                result = result.replace('\\', '/')
            return result
        
        # 没有引号，返回整个字符串
        if normalize_path:
            s = s.replace('\\', '/')
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
                # 路径规范化（Windows 反斜杠转正斜杠）
                file_path = args_str[1:end_quote].replace('\\', '/')
                # 找到逗号分隔符
                rest = args_str[end_quote+1:].strip()
                if rest.startswith(','):
                    content = rest[1:].strip()
                    # 内容不规范化路径，只提取字符串
                    content = self._extract_string_arg(content, normalize_path=False)
                    # 处理转义字符
                    content = self._unescape(content)
                    return (file_path, content)
        
        # 情况2: 没有引号，按第一个逗号分割
        comma_pos = args_str.find(',')
        if comma_pos > 0:
            file_path = args_str[:comma_pos].strip().replace('\\', '/')
            content = args_str[comma_pos+1:].strip()
            content = self._extract_string_arg(content, normalize_path=False)
            content = self._unescape(content)
            return (file_path, content)
        
        # 情况3: 只有一个参数
        return (self._extract_string_arg(args_str, normalize_path=True), "")
    
    def _unescape(self, s: str) -> str:
        """
        处理转义字符
        
        Args:
            s: 包含转义字符的字符串
        
        Returns:
            处理后的字符串
        """
        # 注意顺序：先处理双反斜杠，避免影响其他转义
        # 使用 codecs 模块安全处理转义
        try:
            import codecs
            # 先替换可能有问题的转义序列
            # 对于文件内容，只处理常见的转义
            result = s
            # 按顺序替换，先处理双反斜杠保护
            result = result.replace('\\\\', '\x00')  # 临时占位
            result = result.replace('\\n', '\n')
            result = result.replace('\\t', '\t')
            result = result.replace('\\"', '"')
            result = result.replace("\\'", "'")
            result = result.replace('\x00', '\\')  # 恢复为单反斜杠
            return result
        except Exception:
            return s  # 出错时返回原字符串