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
                print("\n❌ 错误：模型未输出有效的 Action 或 final_answer")
                print(f"   模型原始输出:\n   {response[:300]}...")
                final_answer = "错误：模型格式错误。请确保输出包含 <action> 或 <final_answer> 标签。"
                break
            
            # 解析并执行 Action
            try:
                tool_name, args = self._parse_action(action)
            except Exception as e:
                print(f"\n❌ 解析 Action 失败: {str(e)}")
                final_answer = f"错误：解析 Action 失败 - {str(e)}"
                break
            
            # 安全显示参数（避免 repr() 触发转义错误）
            try:
                # 使用 str() 而不是 repr()，截断长字符串
                args_display = ', '.join(
                    str(a)[:30] + ('...' if len(str(a)) > 30 else '') 
                    for a in args
                ) if args else ''
            except Exception:
                args_display = '(参数显示失败)'
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
        
        # 单字符串参数工具（整个参数就是一个字符串）
        single_arg_tools = {
            "run_command", "list_files", "read_file", "delete_file",
            "mkdir", "git_status", "git_log", "memory_load", "memory_list",
            "get_env", "web_search", "ask_user"
        }
        
        if tool_name in single_arg_tools:
            arg = self._extract_string_arg(args_str, normalize_path=False)
            return (tool_name, (arg,) if arg else ())
        
        # write_file: 需要两个参数 - 文件路径和内容
        if tool_name == "write_file":
            file_path, content = self._parse_write_file_args(args_str)
            return (tool_name, (file_path, content))
        
        # edit_file: 多参数，需要解析
        if tool_name == "edit_file":
            args = self._parse_multi_args(args_str)
            return (tool_name, tuple(args))
        
        # git_diff: 可选参数
        if tool_name == "git_diff":
            args = self._parse_multi_args(args_str)
            return (tool_name, tuple(args))
        
        # http_get/http_post: 可能有字典参数
        if tool_name in ("http_get", "http_post"):
            args = self._parse_multi_args(args_str)
            return (tool_name, tuple(args))
        
        # memory_save: 多参数
        if tool_name == "memory_save":
            args = self._parse_multi_args(args_str)
            return (tool_name, tuple(args))
        
        # search_code/find_files: 多参数
        if tool_name in ("search_code", "find_files"):
            args = self._parse_multi_args(args_str)
            return (tool_name, tuple(args))
        
        # 默认处理
        return (tool_name, (args_str,))
    
    def _parse_multi_args(self, args_str: str) -> list:
        """
        解析多参数字符串，支持字符串、数字、布尔值、None、字典
        
        Args:
            args_str: 参数字符串
        
        Returns:
            参数列表
        """
        import json
        args = []
        current_arg = ""
        in_quotes = False
        quote_char = None
        brace_depth = 0  # 用于处理嵌套的字典/列表
        
        for char in args_str:
            if char in ('"', "'") and not in_quotes and brace_depth == 0:
                in_quotes = True
                quote_char = char
                current_arg += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current_arg += char
            elif char in '{[' and not in_quotes:
                brace_depth += 1
                current_arg += char
            elif char in '}]' and not in_quotes:
                brace_depth -= 1
                current_arg += char
            elif char == ',' and not in_quotes and brace_depth == 0:
                # 分隔符，解析当前参数
                args.append(self._parse_single_arg(current_arg.strip()))
                current_arg = ""
            else:
                current_arg += char
        
        # 最后一个参数
        if current_arg.strip():
            args.append(self._parse_single_arg(current_arg.strip()))
        
        return args
    
    def _parse_single_arg(self, arg: str):
        """
        解析单个参数值，支持关键字参数
        
        Args:
            arg: 参数字符串，可能是 "value" 或 "key=value"
        
        Returns:
            解析后的值（关键字参数返回元组 (key, value)）
        """
        import json
        arg = arg.strip()
        
        # 空值
        if not arg or arg == "None":
            return None
        
        # 检查是否是关键字参数 (key=value)
        # 格式: key="value" 或 key=value 或 key={'dict': 'value'}
        eq_pos = arg.find('=')
        if eq_pos > 0:
            key_part = arg[:eq_pos].strip()
            value_part = arg[eq_pos+1:].strip()
            
            # key 必须是合法的标识符
            if key_part and (key_part[0].isalpha() or key_part[0] == '_'):
                is_valid_key = all(c.isalnum() or c == '_' for c in key_part)
                if is_valid_key:
                    # 递归解析值
                    parsed_value = self._parse_single_arg(value_part)
                    return (key_part, parsed_value)
        
        # 布尔值
        if arg.lower() == "true":
            return True
        if arg.lower() == "false":
            return False
        
        # 字符串（带引号）
        if (arg.startswith('"') and arg.endswith('"')) or \
           (arg.startswith("'") and arg.endswith("'")):
            return self._unescape(arg[1:-1])
        
        # 数字
        try:
            if '.' in arg:
                return float(arg)
            return int(arg)
        except ValueError:
            pass
        
        # 字典/列表
        if arg.startswith('{') or arg.startswith('['):
            try:
                return json.loads(arg)
            except:
                pass
        
        # 默认作为字符串
        return arg
    
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
        try:
            return self._do_extract_string_arg(s, normalize_path)
        except Exception as e:
            print(f"⚠️ _extract_string_arg 错误: {e}")
            return s  # 返回原字符串
    
    def _do_extract_string_arg(self, s: str, normalize_path: bool = False) -> str:
        """实际提取逻辑"""
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
        try:
            return self._do_parse_write_file_args(args_str)
        except Exception as e:
            print(f"⚠️ _parse_write_file_args 错误: {e}")
            # 返回空内容，避免崩溃
            return ("unknown", "")
    
    def _do_parse_write_file_args(self, args_str: str) -> Tuple[str, str]:
        """实际解析逻辑"""
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
        处理转义字符 - 只处理常见的转义序列
        
        Args:
            s: 包含转义字符的字符串
        
        Returns:
            处理后的字符串
        """
        if not s:
            return s
        
        try:
            # 只处理明确的转义序列，不使用 codecs
            # 注意：先替换双反斜杠保护它们
            result = s
            
            # 使用字典映射，避免多次遍历
            escape_map = {
                '\\n': '\n',
                '\\t': '\t',
                '\\r': '\r',
                '\\"': '"',
                "\\'": "'",
            }
            
            # 先处理双反斜杠（保护它们）
            DOUBLE_BACKSLASH = '\x00BACKSLASH\x00'
            result = result.replace('\\\\', DOUBLE_BACKSLASH)
            
            # 处理其他转义
            for old, new in escape_map.items():
                result = result.replace(old, new)
            
            # 恢复双反斜杠为单反斜杠
            result = result.replace(DOUBLE_BACKSLASH, '\\')
            
            return result
            
        except Exception as e:
            # 任何错误都返回原字符串
            print(f"⚠️ _unescape 错误: {e}")
            return s