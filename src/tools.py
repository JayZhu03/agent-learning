"""
工具模块 v1.3

定义 Agent 可以使用的工具函数
包含：文件操作、代码搜索、Git、HTTP、记忆等
集成权限检查和记忆记录
"""

import os
import re
import json
import subprocess
import glob as glob_module
import fnmatch as fnmatch_module
from typing import List, Callable, Dict, Optional, Any, Tuple, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .permissions import Permissions
    from .memory import Memory


class Tools:
    """
    工具集合
    
    管理 Agent 可用的所有工具
    集成权限检查和记忆记录
    """
    
    def __init__(
        self, 
        work_directory: str = ".",
        permissions: Optional["Permissions"] = None,
        memory: Optional["Memory"] = None
    ):
        """
        初始化工具集
        
        Args:
            work_directory: 工作目录，所有文件操作都在这个目录下进行
            permissions: 权限管理器（可选）
            memory: 记忆管理器（可选）
        """
        self.work_directory = os.path.abspath(work_directory)
        self.permissions = permissions
        self.memory = memory
        self.interactive = True  # 是否交互模式
        
        # 记忆存储路径
        self.agent_memory_file = os.path.join(self.work_directory, ".agent_memory.json")
        
        # 注册所有工具
        self.tools: Dict[str, Callable] = {
            # 文件操作
            "read_file": self.read_file,
            "write_file": self.write_file,
            "edit_file": self.edit_file,
            "delete_file": self.delete_file,
            "list_files": self.list_files,
            "find_files": self.find_files,
            "search_code": self.search_code,
            "mkdir": self.mkdir,
            
            # 命令执行
            "run_command": self.run_command,
            
            # Git 操作
            "git_status": self.git_status,
            "git_diff": self.git_diff,
            "git_log": self.git_log,
            
            # HTTP 请求
            "http_get": self.http_get,
            "http_post": self.http_post,
            
            # 环境变量
            "get_env": self.get_env,
            
            # Agent 记忆系统（独立于 Memory 模块）
            "memory_save": self.memory_save,
            "memory_load": self.memory_load,
            "memory_list": self.memory_list,
            
            # 用户交互
            "ask_user": self.ask_user,
            
            # 网络搜索
            "web_search": self.web_search,
        }
    
    # ========== 路径处理 ==========
    
    def _resolve_path(self, file_path: str) -> str:
        """解析路径为绝对路径，并检查是否在工作目录内"""
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.work_directory, file_path)
        
        abs_path = os.path.abspath(file_path)
        if not abs_path.startswith(self.work_directory):
            raise PermissionError(f"路径超出工作目录范围: {abs_path}")
        
        return abs_path
    
    # ========== 文件操作 ==========
    
    def read_file(self, file_path: str, start_line: int = 1, end_line: int = None) -> str:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径
            start_line: 起始行号（从1开始）
            end_line: 结束行号（不指定则读到末尾）
        
        Returns:
            文件内容
        """
        try:
            abs_path = self._resolve_path(file_path)
            
            if not os.path.exists(abs_path):
                return f"错误：文件不存在 {abs_path}"
            
            with open(abs_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # 行号转换
            start_idx = max(0, start_line - 1)
            end_idx = end_line if end_line else len(lines)
            
            selected_lines = lines[start_idx:end_idx]
            
            result = f"文件 {abs_path} (第 {start_line}-{end_line or len(lines)} 行):\n"
            result += "-" * 50 + "\n"
            for i, line in enumerate(selected_lines, start=start_line):
                result += f"{i:4d} | {line}"
            
            return result
        
        except PermissionError as e:
            return f"错误：{str(e)}"
        except Exception as e:
            return f"读取文件错误：{str(e)}"
    
    def write_file(self, file_path: str, content: str) -> str:
        """
        写入文件（覆盖）
        
        Args:
            file_path: 文件路径
            content: 要写入的内容
        
        Returns:
            操作结果
        """
        try:
            abs_path = self._resolve_path(file_path)
            
            # 创建父目录
            parent_dir = os.path.dirname(abs_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return f"✅ 成功写入文件：{abs_path} ({len(content)} 字符)"
        
        except PermissionError as e:
            return f"错误：{str(e)}"
        except Exception as e:
            return f"写入文件错误：{str(e)}"
    
    def edit_file(self, file_path: str, mode: str, old_text: str = None, 
                  new_text: str = None, line_start: int = None, 
                  line_end: int = None) -> str:
        """
        编辑文件（精确修改）
        
        Args:
            file_path: 文件路径
            mode: 编辑模式 - "replace"(替换文本), "insert"(插入行), "delete"(删除行)
            old_text: 要替换的旧文本（mode=replace 时必填）
            new_text: 新文本（mode=replace/insert 时必填）
            line_start: 起始行号（mode=insert/delete 时必填）
            line_end: 结束行号（mode=delete 时可选，默认等于 line_start）
        
        Returns:
            操作结果
        """
        try:
            abs_path = self._resolve_path(file_path)
            
            if not os.path.exists(abs_path):
                return f"错误：文件不存在 {abs_path}"
            
            with open(abs_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            original_count = len(lines)
            
            if mode == "replace":
                if old_text is None:
                    return "错误：replace 模式需要 old_text 参数"
                
                new_lines = []
                replacements = 0
                for line in lines:
                    if old_text in line:
                        new_lines.append(line.replace(old_text, new_text or ""))
                        replacements += 1
                    else:
                        new_lines.append(line)
                
                lines = new_lines
                
                if replacements == 0:
                    return f"未找到匹配文本：{old_text[:50]}..."
                
                result_msg = f"✅ 替换了 {replacements} 处匹配"
            
            elif mode == "insert":
                if line_start is None or new_text is None:
                    return "错误：insert 模式需要 line_start 和 new_text 参数"
                
                # 在 line_start 行之前插入
                insert_idx = max(0, min(line_start - 1, len(lines)))
                lines.insert(insert_idx, new_text + "\n")
                result_msg = f"✅ 在第 {line_start} 行之前插入内容"
            
            elif mode == "delete":
                if line_start is None:
                    return "错误：delete 模式需要 line_start 参数"
                
                line_end = line_end or line_start
                start_idx = max(0, line_start - 1)
                end_idx = min(len(lines), line_end)
                
                deleted_count = end_idx - start_idx
                del lines[start_idx:end_idx]
                
                result_msg = f"✅ 删除了第 {line_start}-{line_end} 行（共 {deleted_count} 行）"
            
            else:
                return f"错误：未知编辑模式 '{mode}'，支持: replace, insert, delete"
            
            # 写回文件
            with open(abs_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            
            return f"{result_msg}，文件：{abs_path}"
        
        except PermissionError as e:
            return f"错误：{str(e)}"
        except Exception as e:
            return f"编辑文件错误：{str(e)}"
    
    def delete_file(self, file_path: str) -> str:
        """
        删除文件或空目录
        
        Args:
            file_path: 文件或目录路径
        
        Returns:
            操作结果
        """
        try:
            abs_path = self._resolve_path(file_path)
            
            if not os.path.exists(abs_path):
                return f"错误：路径不存在 {abs_path}"
            
            if os.path.isfile(abs_path):
                os.remove(abs_path)
                return f"✅ 已删除文件：{abs_path}"
            
            if os.path.isdir(abs_path):
                # 只允许删除空目录
                if os.listdir(abs_path):
                    return f"错误：目录不为空，请先清空目录内容"
                os.rmdir(abs_path)
                return f"✅ 已删除空目录：{abs_path}"
            
            return f"错误：未知类型 {abs_path}"
        
        except PermissionError as e:
            return f"错误：{str(e)}"
        except Exception as e:
            return f"删除错误：{str(e)}"
    
    def list_files(self, directory: str = ".", show_hidden: bool = False) -> str:
        """
        列出目录下的文件
        
        Args:
            directory: 目录路径
            show_hidden: 是否显示隐藏文件
        
        Returns:
            文件列表
        """
        try:
            abs_path = self._resolve_path(directory)
            
            if not os.path.exists(abs_path):
                return f"错误：目录不存在 {abs_path}"
            
            if not os.path.isdir(abs_path):
                return f"错误：不是目录 {abs_path}"
            
            files = os.listdir(abs_path)
            if not show_hidden:
                files = [f for f in files if not f.startswith(".")]
            
            result = f"目录 {abs_path}:\n"
            result += "-" * 50 + "\n"
            
            for f in sorted(files):
                path = os.path.join(abs_path, f)
                if os.path.isdir(path):
                    result += f"📁 {f}/\n"
                else:
                    size = os.path.getsize(path)
                    result += f"📄 {f} ({self._format_size(size)})\n"
            
            return result
        
        except PermissionError as e:
            return f"错误：{str(e)}"
        except Exception as e:
            return f"列出文件错误：{str(e)}"
    
    def find_files(self, pattern: str, directory: str = ".") -> str:
        """
        按模式查找文件
        
        Args:
            pattern: 文件模式，如 "*.py", "test_*.js"
            directory: 搜索起始目录
        
        Returns:
            匹配的文件列表
        """
        try:
            abs_dir = self._resolve_path(directory)
            
            if not os.path.exists(abs_dir):
                return f"错误：目录不存在 {abs_dir}"
            
            # 递归搜索
            matches = []
            for root, dirs, files in os.walk(abs_dir):
                # 跳过隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                
                for f in files:
                    if fnmatch_module.fnmatch(f, pattern):
                        rel_path = os.path.relpath(os.path.join(root, f), abs_dir)
                        matches.append(rel_path)
            
            if not matches:
                return f"未找到匹配 '{pattern}' 的文件"
            
            result = f"找到 {len(matches)} 个匹配 '{pattern}' 的文件:\n"
            result += "-" * 50 + "\n"
            for m in sorted(matches)[:50]:  # 最多显示50个
                result += f"  📄 {m}\n"
            
            if len(matches) > 50:
                result += f"  ... 还有 {len(matches) - 50} 个文件\n"
            
            return result
        
        except PermissionError as e:
            return f"错误：{str(e)}"
        except Exception as e:
            return f"查找文件错误：{str(e)}"
    
    def search_code(self, query: str, directory: str = ".", 
                    file_pattern: str = "*", ignore_case: bool = True) -> str:
        """
        搜索代码内容
        
        Args:
            query: 搜索内容
            directory: 搜索目录
            file_pattern: 文件模式，如 "*.py"
            ignore_case: 是否忽略大小写
        
        Returns:
            匹配结果
        """
        try:
            abs_dir = self._resolve_path(directory)
            
            if not os.path.exists(abs_dir):
                return f"错误：目录不存在 {abs_dir}"
            
            matches = []
            flags = re.IGNORECASE if ignore_case else 0
            
            try:
                pattern = re.compile(query, flags)
            except re.error:
                # 如果不是正则，按字面匹配
                pattern = re.compile(re.escape(query), flags)
            
            for root, dirs, files in os.walk(abs_dir):
                # 跳过隐藏目录和常见排除目录
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in 
                          ["node_modules", "venv", "__pycache__", ".git"]]
                
                for f in files:
                    if not fnmatch_module.fnmatch(f, file_pattern):
                        continue
                    
                    file_path = os.path.join(root, f)
                    rel_path = os.path.relpath(file_path, abs_dir)
                    
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                            for line_num, line in enumerate(fp, 1):
                                if pattern.search(line):
                                    matches.append((rel_path, line_num, line.rstrip()))
                    except:
                        continue
            
            if not matches:
                return f"未找到匹配 '{query}' 的内容"
            
            result = f"搜索 '{query}' 找到 {len(matches)} 处匹配:\n"
            result += "-" * 50 + "\n"
            
            # 按文件分组显示
            current_file = None
            for rel_path, line_num, line in matches[:30]:  # 最多显示30个
                if rel_path != current_file:
                    result += f"\n📄 {rel_path}:\n"
                    current_file = rel_path
                result += f"  {line_num:4d} | {line[:100]}{'...' if len(line) > 100 else ''}\n"
            
            if len(matches) > 30:
                result += f"\n... 还有 {len(matches) - 30} 处匹配\n"
            
            return result
        
        except PermissionError as e:
            return f"错误：{str(e)}"
        except Exception as e:
            return f"搜索错误：{str(e)}"
    
    def mkdir(self, directory: str) -> str:
        """
        创建目录（支持多级）
        
        Args:
            directory: 目录路径
        
        Returns:
            操作结果
        """
        try:
            abs_path = self._resolve_path(directory)
            
            if os.path.exists(abs_path):
                return f"目录已存在：{abs_path}"
            
            os.makedirs(abs_path, exist_ok=True)
            return f"✅ 创建目录：{abs_path}"
        
        except PermissionError as e:
            return f"错误：{str(e)}"
        except Exception as e:
            return f"创建目录错误：{str(e)}"
    
    # ========== 命令执行 ==========
    
    def run_command(self, command: str, timeout: int = 60) -> str:
        """
        执行终端命令
        
        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）
        
        Returns:
            命令输出
        """
        # 危险命令检查（使用单词边界匹配）
        dangerous_patterns = [
            r"\brm\s+-rf\b",
            r"\brm\s+-fr\b",
            r"\bsudo\b",
            r"\bmkfs\b",
            r"\bdd\s+if=",
            r">\s*/dev/",
            r"\bshutdown\b",
            r"\breboot\b",
            r"\binit\s+0\b",
            r"\binit\s+6\b",
            r"\bformat\b",
            r"\bdel\s+/",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return f"⚠️ 警告：命令包含危险操作，已拒绝执行。如需执行请手动操作。"
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.work_directory,
                timeout=timeout
            )
            
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            
            if not output.strip():
                output = "命令执行成功（无输出）"
            
            if result.returncode == 0:
                return f"✅ 执行成功:\n{output}"
            else:
                return f"❌ 执行失败 (退出码 {result.returncode}):\n{output}"
        
        except subprocess.TimeoutExpired:
            return f"⏱️ 命令执行超时（{timeout}秒）"
        except Exception as e:
            return f"执行命令错误：{str(e)}"
    
    # ========== Git 操作 ==========
    
    def git_status(self) -> str:
        """
        查看 Git 状态
        
        Returns:
            Git 状态信息
        """
        try:
            # 先检查是否是 Git 仓库
            check = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                cwd=self.work_directory,
                timeout=5
            )
            
            if check.returncode != 0:
                return "⚠️ 当前目录不是 Git 仓库。请先执行 `git init` 初始化仓库。"
            
            result = subprocess.run(
                ["git", "status", "--short", "--branch"],
                capture_output=True,
                text=True,
                cwd=self.work_directory,
                timeout=10
            )
            
            if result.returncode != 0:
                return f"Git 状态错误：{result.stderr}"
            
            return f"Git 状态:\n{result.stdout or '工作区干净'}"
        
        except subprocess.TimeoutExpired:
            return "Git 命令超时"
        except FileNotFoundError:
            return "⚠️ 未找到 Git 命令，请确保 Git 已安装"
        except Exception as e:
            return f"Git 错误：{str(e)}"
    
    def git_diff(self, file_path: str = None, staged: bool = False) -> str:
        """
        查看 Git 差异
        
        Args:
            file_path: 文件路径（可选，不指定则显示全部差异）
            staged: 是否查看已暂存的更改
        
        Returns:
            Git 差异信息
        """
        try:
            # 先检查是否是 Git 仓库
            check = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                cwd=self.work_directory,
                timeout=5
            )
            
            if check.returncode != 0:
                return "⚠️ 当前目录不是 Git 仓库。请先执行 `git init` 初始化仓库。"
            
            cmd = ["git", "diff"]
            if staged:
                cmd.append("--staged")
            if file_path:
                abs_path = self._resolve_path(file_path)
                cmd.append(abs_path)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.work_directory,
                timeout=10
            )
            
            if result.returncode != 0:
                return f"Git diff 错误：{result.stderr}"
            
            diff = result.stdout.strip()
            if not diff:
                return "无差异"
            
            # 限制输出长度
            if len(diff) > 3000:
                diff = diff[:3000] + "\n... (差异过长，已截断)"
            
            return f"Git 差异:\n{diff}"
        
        except subprocess.TimeoutExpired:
            return "Git 命令超时"
        except Exception as e:
            return f"Git 错误：{str(e)}"
    
    def git_log(self, count: int = 10, oneline: bool = True) -> str:
        """
        查看 Git 日志
        
        Args:
            count: 显示的提交数量
            oneline: 是否使用单行格式
        
        Returns:
            Git 日志
        """
        try:
            # 先检查是否是 Git 仓库
            check = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                cwd=self.work_directory,
                timeout=5
            )
            
            if check.returncode != 0:
                return "⚠️ 当前目录不是 Git 仓库。请先执行 `git init` 初始化仓库。"
            
            cmd = ["git", "log"]
            if oneline:
                cmd.extend(["--oneline", f"-{count}"])
            else:
                cmd.extend([f"-{count}"])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.work_directory,
                timeout=10
            )
            
            if result.returncode != 0:
                return f"Git log 错误：{result.stderr}"
            
            log = result.stdout.strip()
            if not log:
                return "无提交历史"
            
            return f"Git 日志 (最近 {count} 条):\n{log}"
        
        except subprocess.TimeoutExpired:
            return "Git 命令超时"
        except Exception as e:
            return f"Git 错误：{str(e)}"
    
    # ========== HTTP 请求 ==========
    
    def http_get(self, url: str, headers: dict = None, timeout: int = 30) -> str:
        """
        发送 HTTP GET 请求
        
        Args:
            url: 请求 URL
            headers: 请求头（可选）
            timeout: 超时时间（秒）
        
        Returns:
            响应内容
        """
        try:
            import urllib.request
            import urllib.error
            
            req = urllib.request.Request(url, headers=headers or {})
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read().decode("utf-8", errors="ignore")
                
                return f"HTTP {response.status} {url}:\n{content[:2000]}{'...' if len(content) > 2000 else ''}"
        
        except urllib.error.HTTPError as e:
            return f"HTTP 错误 {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            return f"URL 错误: {e.reason}"
        except Exception as e:
            return f"请求错误：{str(e)}"
    
    def http_post(self, url: str, data: dict = None, json_data: dict = None,
                  headers: dict = None, timeout: int = 30) -> str:
        """
        发送 HTTP POST 请求
        
        Args:
            url: 请求 URL
            data: 表单数据（字典）
            json_data: JSON 数据（字典）
            headers: 请求头（字典）
            timeout: 超时时间
        
        Returns:
            响应内容
        """
        try:
            import urllib.request
            import urllib.parse
            
            req_headers = headers or {}
            if not isinstance(req_headers, dict):
                req_headers = {}
            
            body = None
            
            if json_data is not None:
                if not isinstance(json_data, dict):
                    return f"错误：json_data 参数必须是字典类型，当前类型: {type(json_data).__name__}"
                req_headers["Content-Type"] = "application/json"
                body = json.dumps(json_data).encode("utf-8")
            elif data is not None:
                if not isinstance(data, dict):
                    return f"错误：data 参数必须是字典类型，当前类型: {type(data).__name__}"
                body = urllib.parse.urlencode(data).encode("utf-8")
            
            req = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read().decode("utf-8", errors="ignore")
                
                return f"HTTP {response.status} {url}:\n{content[:2000]}{'...' if len(content) > 2000 else ''}"
        
        except Exception as e:
            return f"请求错误：{str(e)}"
    
    # ========== 环境变量 ==========
    
    def get_env(self, key: str = None) -> str:
        """
        获取环境变量
        
        Args:
            key: 环境变量名（可选，不指定则列出所有）
        
        Returns:
            环境变量值
        """
        if key:
            value = os.getenv(key)
            if value:
                # 脱敏敏感信息
                if any(s in key.upper() for s in ["KEY", "TOKEN", "SECRET", "PASSWORD", "PASS"]):
                    return f"{key}=***（已脱敏）"
                return f"{key}={value}"
            return f"环境变量 {key} 未设置"
        else:
            # 列出所有环境变量
            env_vars = dict(os.environ)
            # 过滤和排序
            safe_vars = {}
            for k, v in sorted(env_vars.items()):
                if any(s in k.upper() for s in ["KEY", "TOKEN", "SECRET", "PASSWORD", "PASS"]):
                    safe_vars[k] = "***"
                else:
                    safe_vars[k] = v
            
            result = "环境变量:\n"
            for k, v in list(safe_vars.items())[:30]:  # 最多显示30个
                result += f"  {k}={v[:50]}{'...' if len(v) > 50 else ''}\n"
            
            if len(safe_vars) > 30:
                result += f"  ... 还有 {len(safe_vars) - 30} 个环境变量\n"
            
            return result
    
    # ========== Agent 记忆系统 ==========
    
    def _load_agent_memory(self) -> dict:
        """加载 Agent 记忆数据"""
        if os.path.exists(self.agent_memory_file):
            try:
                with open(self.agent_memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_agent_memory(self, data: dict) -> None:
        """保存 Agent 记忆数据"""
        with open(self.agent_memory_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def memory_save(self, key: str, value: str, category: str = "general") -> str:
        """
        保存记忆
        
        Args:
            key: 记忆键名
            value: 记忆内容
            category: 分类（general, preference, project, error, etc.）
        
        Returns:
            操作结果
        """
        try:
            memory = self._load_agent_memory()
            
            if category not in memory:
                memory[category] = {}
            
            memory[category][key] = {
                "value": value,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            self._save_agent_memory(memory)
            return f"✅ 已保存记忆 [{category}] {key}"
        
        except Exception as e:
            return f"保存记忆错误：{str(e)}"
    
    def memory_load(self, key: str = None, category: str = None) -> str:
        """
        加载记忆
        
        Args:
            key: 记忆键名（可选）
            category: 分类（可选）
        
        Returns:
            记忆内容
        """
        try:
            memory = self._load_agent_memory()
            
            if not memory:
                return "暂无记忆"
            
            if category and key:
                # 查找特定记忆
                if category in memory and key in memory[category]:
                    item = memory[category][key]
                    return f"[{category}] {key}:\n{item['value']}\n(保存于 {item['created_at']})"
                return f"未找到记忆 [{category}] {key}"
            
            elif category:
                # 列出分类下所有记忆
                if category not in memory:
                    return f"分类 [{category}] 下暂无记忆"
                
                result = f"分类 [{category}] 的记忆:\n"
                for k, v in memory[category].items():
                    result += f"  - {k}: {v['value'][:100]}{'...' if len(v['value']) > 100 else ''}\n"
                return result
            
            elif key:
                # 搜索所有分类中的 key
                for cat, items in memory.items():
                    if key in items:
                        item = items[key]
                        return f"[{cat}] {key}:\n{item['value']}\n(保存于 {item['created_at']})"
                return f"未找到记忆 {key}"
            
            else:
                # 列出所有记忆
                result = "所有记忆:\n"
                for cat, items in memory.items():
                    result += f"\n[{cat}]\n"
                    for k, v in items.items():
                        result += f"  - {k}: {v['value'][:50]}{'...' if len(v['value']) > 50 else ''}\n"
                return result
        
        except Exception as e:
            return f"加载记忆错误：{str(e)}"
    
    def memory_list(self) -> str:
        """
        列出所有记忆分类和键
        
        Returns:
            记忆概览
        """
        try:
            memory = self._load_agent_memory()
            
            if not memory:
                return "暂无记忆"
            
            result = "记忆概览:\n"
            total = 0
            for cat, items in memory.items():
                count = len(items)
                total += count
                result += f"  [{cat}] {count} 条记忆\n"
            
            result += f"\n共 {total} 条记忆"
            return result
        
        except Exception as e:
            return f"列出记忆错误：{str(e)}"
    
    # ========== 用户交互 ==========
    
    def ask_user(self, question: str, options: list = None) -> str:
        """
        向用户提问并等待回复
        
        Args:
            question: 问题内容
            options: 可选选项列表
        
        Returns:
            返回特殊标记，表示需要用户输入
        """
        result = f"❓ 需要用户确认：{question}"
        
        if options:
            result += f"\n选项: {', '.join(options)}"
        
        result += "\n[ASK_USER_AWAITING_RESPONSE]"
        
        return result
    
    # ========== 网络搜索 ==========
    
    def web_search(self, query: str, count: int = 5) -> str:
        """
        网络搜索（使用 DuckDuckGo API）
        
        Args:
            query: 搜索关键词
            count: 结果数量
        
        Returns:
            搜索结果
        """
        try:
            import urllib.request
            import urllib.parse
            
            # 使用 DuckDuckGo Instant Answer API
            encoded_query = urllib.parse.quote(query)
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"
            
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; CodingAgent/1.3)"}
            )
            
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
            
            results = []
            
            # 提取相关主题
            if data.get("RelatedTopics"):
                for topic in data["RelatedTopics"][:count]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append({
                            "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                            "snippet": topic.get("Text", ""),
                            "url": topic.get("FirstURL", "")
                        })
            
            # 提取摘要
            if data.get("Abstract"):
                results.insert(0, {
                    "title": "摘要",
                    "snippet": data["Abstract"],
                    "url": data.get("AbstractURL", "")
                })
            
            if not results:
                return f"未找到 '{query}' 的相关结果"
            
            output = f"搜索 '{query}' 结果:\n"
            output += "-" * 50 + "\n"
            
            for i, r in enumerate(results, 1):
                output += f"\n{i}. {r['title']}\n"
                output += f"   {r['snippet'][:200]}{'...' if len(r['snippet']) > 200 else ''}\n"
                if r['url']:
                    output += f"   🔗 {r['url']}\n"
            
            return output
        
        except Exception as e:
            return f"搜索错误：{str(e)}\n提示：如果网络不可用，请尝试其他方式获取信息"
    
    # ========== 工具描述 ==========
    
    def get_tool_description(self) -> str:
        """
        获取所有工具的描述
        
        Returns:
            工具描述字符串，用于 System Prompt
        """
        descriptions = [
            "【文件操作】",
            "- read_file(file_path, start_line=1, end_line=None): 读取文件内容，可指定行范围",
            "- write_file(file_path, content): 写入文件（覆盖）",
            "- edit_file(file_path, mode, old_text=None, new_text=None, line_start=None, line_end=None): 编辑文件",
            "  - mode: 'replace'(替换文本), 'insert'(插入行), 'delete'(删除行)",
            "- delete_file(file_path): 删除文件或空目录",
            "- list_files(directory='.', show_hidden=False): 列出目录内容",
            "- find_files(pattern, directory='.'): 按模式查找文件，如 '*.py'",
            "- search_code(query, directory='.', file_pattern='*', ignore_case=True): 搜索代码内容",
            "- mkdir(directory): 创建目录（支持多级）",
            "",
            "【命令执行】",
            "- run_command(command, timeout=60): 执行终端命令",
            "",
            "【Git 操作】",
            "- git_status(): 查看 Git 状态",
            "- git_diff(file_path=None, staged=False): 查看差异",
            "- git_log(count=10, oneline=True): 查看提交日志",
            "",
            "【HTTP 请求】",
            "- http_get(url, headers=None, timeout=30): GET 请求",
            "- http_post(url, data=None, json_data=None, headers=None, timeout=30): POST 请求",
            "",
            "【环境变量】",
            "- get_env(key=None): 获取环境变量",
            "",
            "【记忆系统】",
            "- memory_save(key, value, category='general'): 保存记忆",
            "- memory_load(key=None, category=None): 加载记忆",
            "- memory_list(): 列出记忆概览",
            "",
            "【用户交互】",
            "- ask_user(question, options=None): 向用户提问，等待确认",
            "",
            "【网络搜索】",
            "- web_search(query, count=5): 网络搜索",
        ]
        return "\n".join(descriptions)
    
    def execute(self, tool_name: str, *args) -> str:
        """
        执行指定工具
        
        Args:
            tool_name: 工具名称
            *args: 工具参数，可包含 (key, value) 元组作为关键字参数
        
        Returns:
            执行结果
        """
        if tool_name not in self.tools:
            return f"错误：未知工具 '{tool_name}'。可用工具: {', '.join(self.tools.keys())}"
        
        # === 分离位置参数和关键字参数 ===
        positional_args = []
        keyword_args = {}
        
        for arg in args:
            if isinstance(arg, tuple) and len(arg) == 2:
                # 关键字参数 (key, value)
                key, value = arg
                if isinstance(key, str):
                    keyword_args[key] = value
                else:
                    positional_args.append(arg)
            else:
                positional_args.append(arg)
        
        # === 权限检查 ===
        if self.permissions:
            try:
                # 对于 write_file，只检查路径，不检查内容（避免转义问题）
                check_args = tuple(positional_args)
                if tool_name == "write_file" and len(positional_args) >= 1:
                    check_args = (positional_args[0],)  # 只传路径
                
                allowed, reason = self.permissions.handle_permission_check(
                    tool_name, *check_args, interactive=self.interactive
                )
                if not allowed:
                    return f"❌ 权限拒绝: {reason}"
            except Exception as e:
                # 权限检查出错，打印详细错误但允许继续
                print(f"⚠️ 权限检查错误: {str(e)}")
                # 非交互模式下拒绝，交互模式下继续执行
                if not self.interactive:
                    return f"❌ 权限检查失败: {str(e)}"
        
        # === 执行工具 ===
        try:
            # 根据是否有 kwargs 选择调用方式
            if keyword_args:
                result = self.tools[tool_name](*positional_args, **keyword_args)
            else:
                result = self.tools[tool_name](*positional_args)
            
            # === 记录记忆 ===
            if self.memory:
                try:
                    self._record_to_memory(tool_name, *positional_args, result=result)
                except Exception as e:
                    # 记录记忆失败不影响工具执行
                    pass  # 静默处理，不打扰用户
            
            return result
        except TypeError as e:
            return f"工具参数错误：{str(e)}\n请检查参数数量和类型"
        except Exception as e:
            import traceback
            traceback.print_exc()  # 打印完整堆栈
            return f"工具执行错误：{str(e)}"
    
    def _record_to_memory(self, tool_name: str, *args, result: str = ""):
        """记录工具调用到记忆"""
        if not self.memory:
            return
        
        if tool_name == "read_file" and args:
            self.memory.record_file_read(args[0])
        
        elif tool_name == "write_file" and len(args) >= 2:
            self.memory.record_file_written(args[0], args[1])
        
        elif tool_name == "run_command" and args:
            success = "成功" in result or "执行成功" in result
            self.memory.record_command(args[0], success=success)
    
    def set_interactive(self, interactive: bool):
        """设置是否交互模式"""
        self.interactive = interactive
    
    # ========== 辅助函数 ==========
    
    @staticmethod
    def _format_size(size: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"