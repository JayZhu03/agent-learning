"""
记忆模块 v2

实现会话分离的记忆系统：
- 每次启动 = 新 session
- 历史会话保留
- 持久上下文跨会话保留
- 摘要模式节省空间
- 支持会话恢复
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class SessionStatus:
    """会话状态"""
    PENDING = "pending"          # 刚创建
    ACTIVE = "active"            # 进行中
    COMPLETED = "completed"      # 正常结束
    INTERRUPTED = "interrupted"  # 被中断（用户退出）


class Memory:
    """
    记忆系统 v2
    
    存储结构：
    - project: 项目信息
    - sessions: 历史会话列表
    - current_session: 当前活跃会话
    - context: 跨会话持久上下文
    """
    
    DEFAULT_MEMORY = {
        "project": {
            "id": None,
            "path": None,
            "name": None,
            "created_at": None
        },
        "sessions": [],  # 历史会话（已完成）
        "current_session": None,  # 当前活跃会话
        "context": {
            "key_files": [],      # 重要文件（跨会话保留）
            "notes": [],          # 笔记（跨会话保留）
            "tech_stack": [],     # 技术栈
            "patterns": []        # 代码模式
        }
    }
    
    MAX_SESSIONS = 20  # 最多保留 20 个历史会话
    MAX_NOTES = 10     # 最多保留 10 条笔记
    MAX_KEY_FILES = 20 # 最多保留 20 个重要文件
    MAX_MESSAGES = 50  # 每个会话最多保留 50 条消息
    
    def __init__(self, work_directory: str = "."):
        """
        初始化记忆系统
        
        Args:
            work_directory: 工作目录
        """
        self.work_directory = os.path.abspath(work_directory)
        
        # 记忆文件路径：.agent/memory.json
        self.agent_dir = os.path.join(self.work_directory, ".agent")
        self.memory_path = os.path.join(self.agent_dir, "memory.json")
        
        # 加载或创建记忆
        self.memory = self._load_or_create()
        
    def _load_or_create(self) -> dict:
        """加载或创建记忆文件"""
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    # 合并默认结构
                    merged = self.DEFAULT_MEMORY.copy()
                    self._deep_merge(merged, saved)
                    return merged
            except Exception as e:
                print(f"⚠️  加载记忆文件失败: {e}，创建新记忆")
        
        # 创建新记忆
        return self._create_new_memory()
    
    def _create_new_memory(self) -> dict:
        """创建新的记忆结构"""
        memory = self.DEFAULT_MEMORY.copy()
        memory["project"] = {
            "id": self._generate_id(),
            "path": self.work_directory,
            "name": os.path.basename(self.work_directory) or "project",
            "created_at": datetime.now().isoformat()
        }
        return memory
    
    def _deep_merge(self, base: dict, override: dict):
        """深度合并字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            elif value is not None:
                base[key] = value
    
    def _generate_id(self) -> str:
        """生成唯一 ID"""
        return str(uuid.uuid4())[:8]
    
    # === 会话管理 ===
    
    def start_session(self, task: str = None) -> str:
        """
        开始新会话
        
        Args:
            task: 任务描述
        
        Returns:
            会话 ID
        """
        # 如果有当前会话，先结束它（标记为中断）
        if self.memory["current_session"]:
            self.interrupt_session()
        
        # 创建新会话
        session_id = self._generate_id()
        self.memory["current_session"] = {
            "id": session_id,
            "status": SessionStatus.ACTIVE,
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "task": task,
            "summary": None,
            "files_read": [],
            "files_written": [],
            "commands": [],
            "messages": [],       # 对话历史
            "success": None
        }
        
        return session_id
    
    def interrupt_session(self):
        """
        中断当前会话（用户退出时调用）
        保存会话状态，以便后续恢复
        """
        current = self.memory["current_session"]
        if not current:
            return
        
        # 标记为中断
        current["status"] = SessionStatus.INTERRUPTED
        current["ended_at"] = datetime.now().isoformat()
        
        # 添加到历史
        self.memory["sessions"].append(current)
        
        # 限制历史会话数量
        if len(self.memory["sessions"]) > self.MAX_SESSIONS:
            self.memory["sessions"] = self.memory["sessions"][-self.MAX_SESSIONS:]
        
        # 清空当前会话
        self.memory["current_session"] = None
        
        # 保存
        self.save()
    
    def end_session(self, summary: str = None, success: bool = True) -> dict:
        """
        结束当前会话
        
        Args:
            summary: 会话摘要
            success: 是否成功
        
        Returns:
            结束的会话
        """
        current = self.memory["current_session"]
        if not current:
            return None
        
        # 结束会话
        current["status"] = SessionStatus.COMPLETED
        current["ended_at"] = datetime.now().isoformat()
        current["summary"] = summary
        current["success"] = success
        
        # 添加到历史
        self.memory["sessions"].append(current)
        
        # 限制历史会话数量
        if len(self.memory["sessions"]) > self.MAX_SESSIONS:
            self.memory["sessions"] = self.memory["sessions"][-self.MAX_SESSIONS:]
        
        # 清空当前会话
        self.memory["current_session"] = None
        
        return current
    
    def get_current_session(self) -> Optional[dict]:
        """获取当前会话"""
        return self.memory["current_session"]
    
    def get_interrupted_sessions(self) -> List[dict]:
        """获取所有中断的会话（可恢复）"""
        return [
            s for s in self.memory["sessions"]
            if s.get("status") == SessionStatus.INTERRUPTED
        ]
    
    def get_last_interrupted_session(self) -> Optional[dict]:
        """获取最后一个中断的会话"""
        interrupted = self.get_interrupted_sessions()
        return interrupted[-1] if interrupted else None
    
    def get_session_by_id(self, session_id: str) -> Optional[dict]:
        """
        根据ID获取会话
        
        Args:
            session_id: 会话ID
        
        Returns:
            会话数据
        """
        # 检查历史会话
        for session in self.memory["sessions"]:
            if session.get("id") == session_id:
                return session
        return None
    
    def resume_session(self, session_id: str = None) -> Optional[dict]:
        """
        恢复会话
        
        Args:
            session_id: 要恢复的会话ID（默认恢复最后一个中断的会话）
        
        Returns:
            恢复的会话，或 None
        """
        # 找到要恢复的会话
        if session_id:
            session = self.get_session_by_id(session_id)
        else:
            session = self.get_last_interrupted_session()
        
        if not session:
            return None
        
        # 从历史中移除
        self.memory["sessions"] = [
            s for s in self.memory["sessions"]
            if s.get("id") != session.get("id")
        ]
        
        # 设置为当前会话
        session["status"] = SessionStatus.ACTIVE
        self.memory["current_session"] = session
        
        return session
    
    def get_recent_sessions(self, limit: int = 5) -> List[dict]:
        """获取最近的会话"""
        return self.memory["sessions"][-limit:]
    
    # === 文件记录 ===
    
    def record_file_read(self, file_path: str):
        """记录文件读取"""
        current = self.memory["current_session"]
        if not current:
            return
        
        rel_path = self._to_relative_path(file_path)
        
        # 避免重复
        if rel_path not in current["files_read"]:
            current["files_read"].append(rel_path)
    
    def record_file_written(self, file_path: str, content: str = ""):
        """记录文件写入"""
        current = self.memory["current_session"]
        if not current:
            return
        
        rel_path = self._to_relative_path(file_path)
        
        # 避免重复
        if rel_path not in current["files_written"]:
            current["files_written"].append(rel_path)
        
        # 添加到重要文件
        self.add_key_file(rel_path)
    
    def add_key_file(self, file_path: str):
        """添加重要文件"""
        rel_path = self._to_relative_path(file_path)
        
        if rel_path not in self.memory["context"]["key_files"]:
            self.memory["context"]["key_files"].append(rel_path)
            
            # 限制数量
            if len(self.memory["context"]["key_files"]) > self.MAX_KEY_FILES:
                self.memory["context"]["key_files"] = \
                    self.memory["context"]["key_files"][-self.MAX_KEY_FILES:]
    
    def get_key_files(self) -> List[str]:
        """获取重要文件列表"""
        return self.memory["context"]["key_files"]
    
    # === 命令记录 ===
    
    def record_command(self, command: str, success: bool = True):
        """记录命令执行"""
        current = self.memory["current_session"]
        if not current:
            return
        
        current["commands"].append({
            "cmd": command[:100],  # 限制长度
            "success": success
        })
    
    # === 消息记录 ===
    
    def add_message(self, role: str, content: str):
        """
        添加消息到当前会话
        
        Args:
            role: 角色 (user/assistant/system)
            content: 消息内容
        """
        current = self.memory["current_session"]
        if not current:
            return
        
        current["messages"].append({
            "role": role,
            "content": content[:2000]  # 限制长度
        })
        
        # 限制消息数量
        if len(current["messages"]) > self.MAX_MESSAGES:
            current["messages"] = current["messages"][-self.MAX_MESSAGES:]
    
    def get_messages(self) -> List[dict]:
        """获取当前会话的消息列表"""
        current = self.memory["current_session"]
        if not current:
            return []
        return current.get("messages", [])
    
    def clear_messages(self):
        """清空当前会话的消息"""
        current = self.memory["current_session"]
        if current:
            current["messages"] = []
    
    # === 笔记 ===
    
    def add_note(self, note: str):
        """添加笔记"""
        if not note:
            return
        
        notes = self.memory["context"]["notes"]
        
        # 避免重复
        for n in notes:
            if n.get("content") == note:
                return
        
        notes.append({
            "content": note[:200],  # 限制长度
            "time": datetime.now().isoformat()
        })
        
        # 限制数量
        if len(notes) > self.MAX_NOTES:
            self.memory["context"]["notes"] = notes[-self.MAX_NOTES:]
    
    def get_notes(self) -> List[dict]:
        """获取所有笔记"""
        return self.memory["context"]["notes"]
    
    # === 技术栈 ===
    
    def add_tech(self, tech: str):
        """添加技术栈"""
        if tech and tech not in self.memory["context"]["tech_stack"]:
            self.memory["context"]["tech_stack"].append(tech)
    
    def get_tech_stack(self) -> List[str]:
        """获取技术栈"""
        return self.memory["context"]["tech_stack"]
    
    # === 上下文摘要 ===
    
    def get_summary(self) -> str:
        """
        获取记忆摘要（用于 Prompt）
        
        Returns:
            记忆摘要文本
        """
        lines = []
        
        # 项目信息
        project = self.memory["project"]
        lines.append(f"📂 项目: {project.get('name', 'Unknown')}")
        
        # 当前会话
        current = self.memory["current_session"]
        if current and current.get("task"):
            lines.append(f"🎯 当前任务: {current['task']}")
        
        # 重要文件
        key_files = self.get_key_files()
        if key_files:
            lines.append(f"📁 重要文件: {', '.join(key_files[-5:])}")
        
        # 技术栈
        tech = self.get_tech_stack()
        if tech:
            lines.append(f"🔧 技术栈: {', '.join(tech)}")
        
        # 笔记
        notes = self.get_notes()
        if notes:
            notes_str = "; ".join([n["content"][:50] for n in notes[-3:]])
            lines.append(f"📝 笔记: {notes_str}")
        
        # 最近会话
        recent = self.get_recent_sessions(2)
        if recent:
            for sess in recent:
                status = "✅" if sess.get("success") else "❌"
                lines.append(f"📋 上次任务: {status} {sess.get('task', 'Unknown')}")
        
        if len(lines) > 1:
            return "【记忆上下文】\n" + "\n".join(lines) + "\n"
        return ""
    
    def get_full_report(self) -> str:
        """获取完整记忆报告"""
        lines = ["=" * 50, "📊 记忆报告", "=" * 50]
        
        # 项目信息
        project = self.memory["project"]
        lines.append(f"\n📂 项目: {project.get('name', 'Unknown')}")
        lines.append(f"   路径: {project.get('path', 'Unknown')}")
        lines.append(f"   创建: {project.get('created_at', 'Unknown')[:19]}")
        
        # 当前会话
        current = self.memory["current_session"]
        if current:
            lines.append(f"\n🎯 当前会话:")
            lines.append(f"   ID: {current.get('id')}")
            lines.append(f"   任务: {current.get('task', 'Unknown')}")
            lines.append(f"   开始: {current.get('started_at', '')[:19]}")
            lines.append(f"   读取: {len(current.get('files_read', []))} 个文件")
            lines.append(f"   写入: {len(current.get('files_written', []))} 个文件")
            lines.append(f"   命令: {len(current.get('commands', []))} 个")
        
        # 历史会话
        sessions = self.memory["sessions"]
        lines.append(f"\n📋 历史会话 ({len(sessions)} 个):")
        for sess in sessions[-5:]:
            status_icon = {
                SessionStatus.COMPLETED: "✅",
                SessionStatus.INTERRUPTED: "⏸️",
                SessionStatus.ACTIVE: "▶️",
                SessionStatus.PENDING: "⏳"
            }.get(sess.get("status"), "❓")
            success_icon = "" if sess.get("success") else "❌" if sess.get("status") == SessionStatus.COMPLETED else ""
            lines.append(f"   {status_icon} {success_icon} {sess.get('task', 'Unknown')[:40]} ({sess.get('id')})")
        
        # 重要文件
        key_files = self.get_key_files()
        if key_files:
            lines.append(f"\n📁 重要文件 ({len(key_files)} 个):")
            for f in key_files[-10:]:
                lines.append(f"   - {f}")
        
        # 技术栈
        tech = self.get_tech_stack()
        if tech:
            lines.append(f"\n🔧 技术栈: {', '.join(tech)}")
        
        # 笔记
        notes = self.get_notes()
        if notes:
            lines.append(f"\n📝 笔记 ({len(notes)} 条):")
            for note in notes[-5:]:
                lines.append(f"   - {note['content']}")
        
        return "\n".join(lines)
    
    # === 持久化 ===
    
    def save(self):
        """保存记忆到文件"""
        try:
            # 确保目录存在
            os.makedirs(self.agent_dir, exist_ok=True)
            
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  保存记忆失败: {e}")
    
    def clear(self):
        """清空记忆（保留项目信息）"""
        project = self.memory["project"]
        self.memory = self.DEFAULT_MEMORY.copy()
        self.memory["project"] = project
        self.memory["project"]["created_at"] = datetime.now().isoformat()
        self.save()
    
    def clear_all(self):
        """完全清空记忆（包括项目信息）"""
        self.memory = self._create_new_memory()
        self.save()
    
    # === 工具方法 ===
    
    def _to_relative_path(self, path: str) -> str:
        """转换为相对路径"""
        if os.path.isabs(path):
            try:
                return os.path.relpath(path, self.work_directory)
            except ValueError:
                return path
        return path
    
    def get_memory_path(self) -> str:
        """获取记忆文件路径"""
        return self.memory_path