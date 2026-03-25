"""
主入口文件

提供命令行接口，启动 Agent
"""

import click
import os
from src.config import Config
from src.agent import CodingAgent


@click.command()
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
def main(dir: str, task: str):
    """
    Coding Agent - 你的 AI 编程助手
    
    使用方法：
    
        # 交互模式
        python -m src.main -d /path/to/project
        
        # 单次任务
        python -m src.main -d /path/to/project -t "创建一个 hello.py 文件"
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
    print(f"{'='*50}")
    
    # 创建 Agent
    agent = CodingAgent(work_dir)
    
    if task:
        # 单次任务模式
        agent.run(task)
    else:
        # 交互模式
        print("\n进入交互模式，输入 'exit' 或 'quit' 退出\n")
        
        while True:
            try:
                user_input = input("👤 你：").strip()
                
                if user_input.lower() in ('exit', 'quit', 'q'):
                    print("\n👋 再见！")
                    break
                
                if not user_input:
                    continue
                
                # 运行 Agent
                agent.run(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 再见！")
                break
            except Exception as e:
                print(f"\n❌ 错误：{str(e)}\n")


if __name__ == "__main__":
    main()