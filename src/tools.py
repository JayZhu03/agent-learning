"""
工具模块

定义 Agent 可以使用的工具函数
包括：读取文件、写入文件、执行命令
"""

import os
import subprocess
from typing import List, Callable, Dict


class Tools:
    """
    工具集合
    
    管理 Agent 可用的所有工具
    """
    
    def __init__(self, work_directory: str = "."):
        """
        初始化工具集
        
        Args:
            work_directory: 工作目录，所有文件操作都在这个目录下进行
        """
        self.work_directory = os.path.abspath(work_directory)
        self.tools: Dict[str, Callable] = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "run_command": self.run_command,
            "list_files": self.list_files,
        }
    
    def read_file(self, file_path: str) -> str:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径（绝对路径或相对路径）
        
        Returns:
            文件内容，或错误信息
        """
        try:
            # 如果是相对路径，转换为绝对路径
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.work_directory, file_path)
            
            # 安全检查：确保文件在工作目录下
            if not os.path.abspath(file_path).startswith(self.work_directory):
                return "错误：不能读取工作目录以外的文件"
            
            if not os.path.exists(file_path):
                return f"错误：文件不存在 {file_path}"
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"文件内容 ({file_path}):\n{content}"
        
        except Exception as e:
            return f"读取文件错误：{str(e)}"
    
    def write_file(self, file_path: str, content: str) -> str:
        """
        写入文件
        
        Args:
            file_path: 文件路径
            content: 要写入的内容
        
        Returns:
            操作结果
        """
        try:
            # 如果是相对路径，转换为绝对路径
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.work_directory, file_path)
            
            # 安全检查
            if not os.path.abspath(file_path).startswith(self.work_directory):
                return "错误：不能写入工作目录以外的文件"
            
            # 创建目录（如果不存在）
            dir_path = os.path.dirname(file_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return f"成功写入文件：{file_path}"
        
        except Exception as e:
            return f"写入文件错误：{str(e)}"
    
    def run_command(self, command: str) -> str:
        """
        执行终端命令
        
        Args:
            command: 要执行的命令
        
        Returns:
            命令输出或错误信息
        """
        # 危险命令列表 - 使用单词边界匹配
        import re
        dangerous_patterns = [
            r'\brm\s+-rf\b',      # rm -rf
            r'\brm\s+-fr\b',      # rm -fr
            r'\bsudo\b',          # sudo
            r'\bmkfs\b',          # mkfs
            r'\bdd\s+',           # dd 命令
            r'>\s*/dev/',         # 写入 /dev
            r'\bformat\b',        # format
            r'\bdel\s+/',         # del /
        ]
        
        # 检查是否包含危险命令
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return f"警告：命令包含危险操作，已拒绝执行"
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.work_directory,
                timeout=60  # 60秒超时
            )
            
            if result.returncode == 0:
                output = result.stdout if result.stdout else "命令执行成功（无输出）"
                return f"执行结果：\n{output}"
            else:
                return f"执行失败（错误码 {result.returncode}）：\n{result.stderr}"
        
        except subprocess.TimeoutExpired:
            return "错误：命令执行超时（60秒）"
        except Exception as e:
            return f"执行命令错误：{str(e)}"
    
    def list_files(self, directory: str = ".") -> str:
        """
        列出目录下的文件
        
        Args:
            directory: 目录路径
        
        Returns:
            文件列表
        """
        try:
            if not os.path.isabs(directory):
                directory = os.path.join(self.work_directory, directory)
            
            if not os.path.exists(directory):
                return f"错误：目录不存在 {directory}"
            
            files = os.listdir(directory)
            result = f"目录 {directory} 下的文件：\n"
            for f in sorted(files):
                path = os.path.join(directory, f)
                if os.path.isdir(path):
                    result += f"  📁 {f}/\n"
                else:
                    size = os.path.getsize(path)
                    result += f"  📄 {f} ({size} bytes)\n"
            return result
        
        except Exception as e:
            return f"列出文件错误：{str(e)}"
    
    def get_tool_description(self) -> str:
        """
        获取所有工具的描述
        
        Returns:
            工具描述字符串，用于 System Prompt
        """
        descriptions = [
            "- read_file(file_path): 读取文件内容。参数：file_path 为文件路径",
            "- write_file(file_path, content): 写入文件。参数：file_path 为文件路径，content 为文件内容（可以包含换行符 \\n）",
            "- run_command(command): 执行终端命令。参数：command 为命令字符串",
            "- list_files(directory): 列出目录文件。参数：directory 为目录路径（默认当前目录）",
        ]
        return "\n".join(descriptions)
    
    def execute(self, tool_name: str, *args) -> str:
        """
        执行指定工具
        
        Args:
            tool_name: 工具名称
            *args: 工具参数
        
        Returns:
            执行结果
        """
        if tool_name not in self.tools:
            return f"错误：未知工具 '{tool_name}'"
        
        try:
            return self.tools[tool_name](*args)
        except Exception as e:
            return f"工具执行错误：{str(e)}"