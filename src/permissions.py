"""
权限模块

管理工具执行权限，支持 allow/ask/deny 三种级别
"""

import json
import os
import re
import fnmatch
from typing import Tuple
from pathlib import Path


class PermissionLevel:
    """权限级别"""
    ALLOW = "allow"   # 直接允许
    ASK = "ask"       # 询问用户
    DENY = "deny"     # 拒绝执行


class Permissions:
    """
    权限管理器
    
    支持：
    - 工具权限：read_file, write_file, run_command, list_files
    - 命令权限：ls*, rm*, git* 等（仅对 run_command 生效）
    - 路径权限：.env, *.key, ~/.ssh/* 等
    """
    
    DEFAULT_PERMISSIONS = {
        "tools": {
            "read_file": "allow",
            "write_file": "ask",
            "run_command": "ask",
            "list_files": "allow"
        },
        "commands": {
            "ls*": "allow",
            "cat*": "allow",
            "git*": "allow",
            "python*": "allow",
            "pip*": "allow",
            "npm*": "allow",
            "rm*": "deny",
            "sudo*": "deny",
            "mkfs*": "deny",
            "dd*": "deny"
        },
        "paths": {
            ".env": "deny",
            ".env.*": "deny",
            "*.key": "deny",
            "*.pem": "deny",
            "~/.ssh/*": "deny",
            "~/.config/*": "ask"
        }
    }
    
    def __init__(self, config_path: str = None, work_directory: str = "."):
        """
        初始化权限管理器
        
        Args:
            config_path: 权限配置文件路径（默认为 .agent/permissions.json）
            work_directory: 工作目录
        """
        self.work_directory = os.path.abspath(work_directory)
        
        # 默认配置文件在 .agent 目录下
        if config_path is None:
            config_path = os.path.join(self.work_directory, ".agent", "permissions.json")
        
        self.config_path = config_path
        self.permissions = self._load_permissions()
        self._session_decisions = {}  # 本次会话的用户决定缓存
        
    def _load_permissions(self) -> dict:
        """加载权限配置"""
        # 尝试从配置文件加载
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 合并默认配置（用户配置优先）
                    merged = self.DEFAULT_PERMISSIONS.copy()
                    for key in ["tools", "commands", "paths"]:
                        if key in config:
                            merged[key] = {**merged.get(key, {}), **config[key]}
                    return merged
            except Exception as e:
                print(f"⚠️  加载权限配置失败: {e}，使用默认配置")
                return self.DEFAULT_PERMISSIONS.copy()
        return self.DEFAULT_PERMISSIONS.copy()
    
    def save_permissions(self):
        """保存权限配置到文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.permissions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  保存权限配置失败: {e}")
    
    def check_tool_permission(self, tool_name: str) -> Tuple[str, str]:
        """
        检查工具权限
        
        Args:
            tool_name: 工具名称
        
        Returns:
            (权限级别, 原因说明)
        """
        # 检查会话缓存
        cache_key = f"tool:{tool_name}"
        if cache_key in self._session_decisions:
            return (self._session_decisions[cache_key], "本次会话已确认")
        
        # 从配置获取
        tool_perms = self.permissions.get("tools", {})
        level = tool_perms.get(tool_name, PermissionLevel.ASK)
        return (level, f"配置规则: tools.{tool_name}")
    
    def check_command_permission(self, command: str) -> Tuple[str, str]:
        """
        检查命令权限（针对 run_command）
        
        Args:
            command: 要执行的命令
        
        Returns:
            (权限级别, 原因说明)
        """
        # 检查会话缓存
        cache_key = f"cmd:{command}"
        if cache_key in self._session_decisions:
            return (self._session_decisions[cache_key], "本次会话已确认")
        
        # 获取命令的第一个词（程序名）
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return (PermissionLevel.ASK, "空命令")
        
        cmd_name = cmd_parts[0]
        
        # 按模式匹配命令权限
        command_perms = self.permissions.get("commands", {})
        matched_rules = []
        
        for pattern, level in command_perms.items():
            if fnmatch.fnmatch(cmd_name, pattern) or fnmatch.fnmatch(command, pattern):
                matched_rules.append((pattern, level))
        
        # 如果匹配到规则，优先级：deny > ask > allow
        if matched_rules:
            # 检查是否有 deny
            for pattern, level in matched_rules:
                if level == PermissionLevel.DENY:
                    return (PermissionLevel.DENY, f"命令匹配规则: commands.{pattern}")
            # 检查是否有 ask
            for pattern, level in matched_rules:
                if level == PermissionLevel.ASK:
                    return (PermissionLevel.ASK, f"命令匹配规则: commands.{pattern}")
            # 否则 allow
            pattern, level = matched_rules[0]
            return (PermissionLevel.ALLOW, f"命令匹配规则: commands.{pattern}")
        
        # 没有匹配规则，默认 ask
        return (PermissionLevel.ASK, "无匹配规则，默认询问")
    
    def check_path_permission(self, path: str, operation: str = "read") -> Tuple[str, str]:
        """
        检查路径权限
        
        Args:
            path: 文件/目录路径
            operation: 操作类型 (read/write)
        
        Returns:
            (权限级别, 原因说明)
        """
        # 展开路径
        expanded_path = os.path.expanduser(path)
        if not os.path.isabs(expanded_path):
            expanded_path = os.path.join(self.work_directory, expanded_path)
        expanded_path = os.path.abspath(expanded_path)
        
        # 检查会话缓存
        cache_key = f"path:{expanded_path}:{operation}"
        if cache_key in self._session_decisions:
            return (self._session_decisions[cache_key], "本次会话已确认")
        
        # 获取文件名和路径
        filename = os.path.basename(expanded_path)
        
        # 路径权限规则
        path_perms = self.permissions.get("paths", {})
        
        for pattern, level in path_perms.items():
            # 展开模式中的 ~ 
            expanded_pattern = os.path.expanduser(pattern)
            
            # 匹配文件名
            if fnmatch.fnmatch(filename, pattern):
                return (level, f"路径匹配规则: paths.{pattern}")
            
            # 匹配完整路径
            if fnmatch.fnmatch(expanded_path, expanded_pattern):
                return (level, f"路径匹配规则: paths.{pattern}")
            
            # 通配符路径匹配
            if "*" in expanded_pattern:
                # 将通配符模式转换为正则
                regex_pattern = expanded_pattern.replace("*", ".*")
                if re.match(regex_pattern, expanded_path):
                    return (level, f"路径匹配规则: paths.{pattern}")
        
        # 工作目录外检查
        if not expanded_path.startswith(self.work_directory):
            return (PermissionLevel.ASK, f"路径在工作目录外")
        
        # 默认允许
        return (PermissionLevel.ALLOW, "路径检查通过")
    
    def ask_user(self, action: str, details: str) -> str:
        """
        询问用户是否允许操作
        
        Args:
            action: 操作描述
            details: 详细信息
        
        Returns:
            用户决定: allow/allow_always/deny/deny_always
        """
        # 安全截断操作描述（避免特殊字符问题）
        safe_action = action[:100] if len(action) > 100 else action
        safe_details = details[:100] if len(details) > 100 else details
        
        print(f"\n⚠️  需要确认操作:")
        print(f"   操作: {safe_action}")
        print(f"   详情: {safe_details}")
        print(f"\n   [y] 允许本次")
        print(f"   [Y] 允许本次会话所有相同操作")
        print(f"   [n] 拒绝本次")
        print(f"   [N] 拒绝本次会话所有相同操作")
        
        while True:
            try:
                choice = input("   请选择 [y/Y/n/N]: ").strip().lower()
                
                if choice == 'y':
                    return 'allow'
                elif choice == 'yes':
                    return 'allow_always'
                elif choice == 'n':
                    return 'deny'
                elif choice == 'no':
                    return 'deny_always'
                else:
                    print("   无效输入，请重新选择")
            except (EOFError, KeyboardInterrupt):
                return 'deny'
    
    def handle_permission_check(
        self, 
        tool_name: str, 
        *args, 
        interactive: bool = True
    ) -> Tuple[bool, str]:
        """
        处理权限检查
        
        Args:
            tool_name: 工具名称
            args: 工具参数
            interactive: 是否交互模式（询问用户）
        
        Returns:
            (是否允许, 原因说明)
        """
        # 1. 检查工具权限
        tool_level, tool_reason = self.check_tool_permission(tool_name)
        
        if tool_level == PermissionLevel.DENY:
            return (False, f"工具被拒绝: {tool_reason}")
        
        # 2. 检查路径权限（read_file, write_file）
        if tool_name in ("read_file", "write_file") and args:
            path = args[0]
            operation = "write" if tool_name == "write_file" else "read"
            path_level, path_reason = self.check_path_permission(path, operation)
            
            if path_level == PermissionLevel.DENY:
                return (False, f"路径被拒绝: {path_reason}")
            
            # 路径需要询问，且工具权限不是 ask 时，也要询问
            if path_level == PermissionLevel.ASK:
                if interactive:
                    decision = self.ask_user(f"{tool_name}({path})", path_reason)
                    return self._handle_user_decision(decision, f"path:{path}:{operation}")
                return (False, f"需要用户确认: {path_reason}")
        
        # 3. 检查命令权限（run_command）
        if tool_name == "run_command" and args:
            command = args[0]
            cmd_level, cmd_reason = self.check_command_permission(command)
            
            if cmd_level == PermissionLevel.DENY:
                return (False, f"命令被拒绝: {cmd_reason}")
        
        # 4. 工具需要询问
        if tool_level == PermissionLevel.ASK:
            if interactive:
                # 安全显示参数（避免特殊字符问题）
                try:
                    args_display = ', '.join(
                        str(a)[:30] + ('...' if len(str(a)) > 30 else '') 
                        for a in args
                    )
                except Exception:
                    args_display = "..."
                decision = self.ask_user(f"{tool_name}({args_display})", tool_reason)
                return self._handle_user_decision(decision, f"tool:{tool_name}")
            return (False, f"需要用户确认: {tool_reason}")
        
        # 允许执行
        return (True, "权限检查通过")
    
    def _handle_user_decision(self, decision: str, cache_key: str) -> Tuple[bool, str]:
        """
        处理用户决定
        
        Args:
            decision: 用户决定
            cache_key: 缓存键
        
        Returns:
            (是否允许, 原因)
        """
        if decision == 'allow':
            return (True, "用户允许本次操作")
        elif decision == 'allow_always':
            self._session_decisions[cache_key] = PermissionLevel.ALLOW
            return (True, "用户允许本次会话所有相同操作")
        elif decision == 'deny':
            return (False, "用户拒绝本次操作")
        elif decision == 'deny_always':
            self._session_decisions[cache_key] = PermissionLevel.DENY
            return (False, "用户拒绝本次会话所有相同操作")
        
        return (False, "未知决定")
    
    def reset_session(self):
        """重置会话缓存"""
        self._session_decisions.clear()