"""
主入口文件

提供命令行接口，启动 Agent
"""

import click
import os
from src.config import Config
from src.agent import CodingAgent
from src.memory import Memory


@click.group()
def cli():
    """Coding Agent - AI 编程助手"""
    pass


@cli.command()
@click.option(
    '--dir', '-d',
    default='.',
    help='工作目录（默认为当前目录）'
)
@click.option(
    '--task', '-t',
    default=None,
    help='要执行的任务（不指定则进入交互模式）'
)
@click.option(
    '--non-interactive',
    is_flag=True,
    help='非交互模式（不询问权限，仅允许 allow 操作）'
)
def run(dir: str, task: str, non_interactive: bool):
    """
    启动 Coding Agent
    
    示例：
    
        # 交互模式
        python -m src.main run -d /path/to/project
        
        # 单次任务
        python -m src.main run -d /path/to/project -t "创建一个 hello.py 文件"
        
        # 非交互模式
        python -m src.main run -d /path/to/project --non-interactive -t "读取 README.md"
    """
    # 验证配置
    if not Config.validate():
        return
    
    # 获取绝对路径
    work_dir = os.path.abspath(dir)
    
    # 检查目录是否存在
    if not os.path.exists(work_dir):
        print(f"错误：目录不存在 {work_dir}")
        return
    
    print(f"\n🤖 Coding Agent 已启动")
    print(f"📁 工作目录：{work_dir}")
    print(f"🧠 模型：{Config.MODEL}")
    print(f"🔒 交互模式：{'关闭' if non_interactive else '开启'}")
    print(f"{'='*50}")
    
    # 创建 Agent
    agent = CodingAgent(work_dir, interactive=not non_interactive)
    
    if task:
        # 单次任务模式
        agent.run(task)
    else:
        # 交互模式
        print("\n进入交互模式，输入 'exit' 或 'quit' 退出")
        print("特殊命令：")
        print("  /memory  - 查看记忆报告")
        print("  /reset   - 清空记忆")
        print("  /note    - 添加笔记")
        print()
        
        while True:
            try:
                user_input = input("👤 你：").strip()
                
                if user_input.lower() in ('exit', 'quit', 'q'):
                    print("\n👋 再见！")
                    break
                
                # 特殊命令
                if user_input == '/memory':
                    print(agent.memory.get_full_report())
                    continue
                
                if user_input == '/reset':
                    agent.memory.clear()
                    agent.permissions.reset_session()
                    print("✅ 已清空记忆和会话权限缓存")
                    continue
                
                if user_input.startswith('/note '):
                    note = user_input[6:].strip()
                    if note:
                        agent.memory.add_note(note)
                        agent.memory.save()
                        print(f"✅ 已添加笔记: {note[:50]}")
                    continue
                
                if not user_input:
                    continue
                
                # 运行 Agent
                agent.run(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 再见！")
                break
            except Exception as e:
                print(f"\n❌ 错误：{str(e)}\n")


@cli.command()
@click.option('--dir', '-d', default='.', help='工作目录')
def memory(dir: str):
    """查看记忆报告"""
    work_dir = os.path.abspath(dir)
    mem = Memory(work_dir)
    print(mem.get_full_report())


@cli.command()
@click.option('--dir', '-d', default='.', help='工作目录')
@click.option('--reset', is_flag=True, help='重置记忆（保留项目信息）')
@click.option('--clear-all', is_flag=True, help='完全清空记忆')
def mem(dir: str, reset: bool, clear_all: bool):
    """管理记忆"""
    work_dir = os.path.abspath(dir)
    mem = Memory(work_dir)
    
    if clear_all:
        mem.clear_all()
        print("✅ 记忆已完全清空")
    elif reset:
        mem.clear()
        print("✅ 记忆已重置（保留项目信息）")
    else:
        print(mem.get_full_report())


@cli.command()
@click.option('--dir', '-d', default='.', help='工作目录')
def perms(dir: str):
    """查看当前权限配置"""
    from src.permissions import Permissions
    work_dir = os.path.abspath(dir)
    
    perms = Permissions(
        config_path=os.path.join(work_dir, ".agent", "permissions.json"),
        work_directory=work_dir
    )
    
    print("📋 权限配置:")
    print(f"\n🔧 工具权限:")
    for tool, level in perms.permissions.get("tools", {}).items():
        icon = "✅" if level == "allow" else "❓" if level == "ask" else "❌"
        print(f"   {icon} {tool}: {level}")
    
    print(f"\n💻 命令权限:")
    for cmd, level in perms.permissions.get("commands", {}).items():
        icon = "✅" if level == "allow" else "❓" if level == "ask" else "❌"
        print(f"   {icon} {cmd}: {level}")
    
    print(f"\n📁 路径权限:")
    for path, level in perms.permissions.get("paths", {}).items():
        icon = "✅" if level == "allow" else "❓" if level == "ask" else "❌"
        print(f"   {icon} {path}: {level}")


@cli.command()
@click.option('--dir', '-d', default='.', help='工作目录')
def init(dir: str):
    """初始化项目的 .agent 目录"""
    work_dir = os.path.abspath(dir)
    agent_dir = os.path.join(work_dir, ".agent")
    
    # 创建目录
    os.makedirs(agent_dir, exist_ok=True)
    
    # 创建 .gitignore
    gitignore_path = os.path.join(agent_dir, ".gitignore")
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w") as f:
            f.write("# Agent memory and config\n")
            f.write("memory.json\n")
            f.write("permissions.json\n")
        print(f"✅ 创建 {gitignore_path}")
    
    # 初始化记忆
    mem = Memory(work_dir)
    mem.save()
    print(f"✅ 创建 {mem.get_memory_path()}")
    
    print(f"\n🎉 项目已初始化！")
    print(f"   目录: {agent_dir}")


if __name__ == "__main__":
    cli()