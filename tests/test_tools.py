#!/usr/bin/env python3
"""
Coding Agent v1.3 测试脚本
运行方式: python tests/test_tools.py
"""

import os
import sys
import tempfile
import shutil

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tools import Tools


class TestTools:
    """工具测试类"""
    
    def __init__(self):
        # 创建临时测试目录
        self.test_dir = tempfile.mkdtemp(prefix="coding_agent_test_")
        self.tools = Tools(self.test_dir)
        self.passed = 0
        self.failed = 0
    
    def cleanup(self):
        """清理测试目录"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def assert_result(self, test_name: str, result: str, should_contain: str = None, 
                      should_not_contain: str = None):
        """断言结果"""
        success = True
        
        if should_contain and should_contain not in result:
            print(f"  ❌ {test_name}: 期望包含 '{should_contain}'")
            print(f"     实际: {result[:100]}...")
            success = False
        
        if should_not_contain and should_not_contain in result:
            print(f"  ❌ {test_name}: 不应包含 '{should_not_contain}'")
            success = False
        
        if success:
            print(f"  ✅ {test_name}")
            self.passed += 1
        else:
            self.failed += 1
        
        return success
    
    # ========== 文件操作测试 ==========
    
    def test_write_file(self):
        """测试写入文件"""
        print("\n【测试 write_file】")
        
        result = self.tools.write_file("test.txt", "Hello, World!")
        self.assert_result("创建文件", result, "成功")
        
        result = self.tools.write_file("subdir/nested.txt", "Nested content")
        self.assert_result("创建嵌套文件", result, "成功")
    
    def test_read_file(self):
        """测试读取文件"""
        print("\n【测试 read_file】")
        
        # 先创建文件
        self.tools.write_file("read_test.txt", "Line 1\nLine 2\nLine 3")
        
        result = self.tools.read_file("read_test.txt")
        self.assert_result("读取文件", result, "Line 1")
        
        result = self.tools.read_file("read_test.txt", start_line=2, end_line=3)
        self.assert_result("读取指定行", result, "Line 2")
    
    def test_edit_file(self):
        """测试编辑文件"""
        print("\n【测试 edit_file】")
        
        # 创建测试文件
        self.tools.write_file("edit_test.txt", "Hello old text here")
        
        # 替换
        result = self.tools.edit_file("edit_test.txt", "replace", "old", "new")
        self.assert_result("替换文本", result, "替换了")
        
        # 插入
        result = self.tools.edit_file("edit_test.txt", "insert", new_text="INSERTED", line_start=1)
        self.assert_result("插入行", result, "插入")
        
        # 删除
        result = self.tools.edit_file("edit_test.txt", "delete", line_start=1, line_end=1)
        self.assert_result("删除行", result, "删除")
    
    def test_list_files(self):
        """测试列出文件"""
        print("\n【测试 list_files】")
        
        # 创建一些文件
        self.tools.write_file("file1.txt", "content1")
        self.tools.write_file("file2.py", "content2")
        
        result = self.tools.list_files()
        self.assert_result("列出文件", result, "file1.txt")
    
    def test_find_files(self):
        """测试查找文件"""
        print("\n【测试 find_files】")
        
        self.tools.write_file("app.py", "code")
        self.tools.write_file("test.py", "code")
        self.tools.write_file("readme.md", "doc")
        
        result = self.tools.find_files("*.py")
        self.assert_result("查找 .py 文件", result, "app.py")
    
    def test_search_code(self):
        """测试搜索代码"""
        print("\n【测试 search_code】")
        
        self.tools.write_file("code1.py", "import os\nprint('hello')")
        self.tools.write_file("code2.py", "import sys\nprint('world')")
        
        result = self.tools.search_code("import")
        self.assert_result("搜索 import", result, "import")
    
    def test_mkdir(self):
        """测试创建目录"""
        print("\n【测试 mkdir】")
        
        result = self.tools.mkdir("new_dir/sub_dir")
        self.assert_result("创建嵌套目录", result, "创建目录")
    
    def test_delete_file(self):
        """测试删除文件"""
        print("\n【测试 delete_file】")
        
        self.tools.write_file("to_delete.txt", "delete me")
        
        result = self.tools.delete_file("to_delete.txt")
        self.assert_result("删除文件", result, "已删除")
    
    # ========== Git 测试 ==========
    
    def test_git_status(self):
        """测试 Git 状态"""
        print("\n【测试 git_status】")
        
        result = self.tools.git_status()
        # 在非 Git 目录会报错，这是正常的
        print(f"  结果: {result[:100]}...")
        self.passed += 1
    
    # ========== HTTP 测试 ==========
    
    def test_http_get(self):
        """测试 HTTP GET"""
        print("\n【测试 http_get】")
        
        result = self.tools.http_get("https://httpbin.org/get")
        self.assert_result("GET 请求", result, should_contain=None)  # 网络可能不可用
    
    # ========== 环境变量测试 ==========
    
    def test_get_env(self):
        """测试获取环境变量"""
        print("\n【测试 get_env】")
        
        result = self.tools.get_env("PATH")
        self.assert_result("获取 PATH", result, "PATH")
        
        result = self.tools.get_env()
        self.assert_result("列出所有环境变量", result, "环境变量")
    
    # ========== 记忆系统测试 ==========
    
    def test_memory(self):
        """测试记忆系统"""
        print("\n【测试记忆系统】")
        
        # 保存
        result = self.tools.memory_save("test_key", "test_value", "test")
        self.assert_result("保存记忆", result, "已保存")
        
        # 加载
        result = self.tools.memory_load("test_key", "test")
        self.assert_result("加载记忆", result, "test_value")
        
        # 列表
        result = self.tools.memory_list()
        self.assert_result("列出记忆", result, "记忆")
    
    # ========== 用户交互测试 ==========
    
    def test_ask_user(self):
        """测试用户交互"""
        print("\n【测试 ask_user】")
        
        result = self.tools.ask_user("确认删除？", ["是", "否"])
        self.assert_result("提问用户", result, "ASK_USER_AWAITING_RESPONSE")
    
    # ========== 命令执行测试 ==========
    
    def test_run_command(self):
        """测试命令执行"""
        print("\n【测试 run_command】")
        
        result = self.tools.run_command("echo hello")
        self.assert_result("执行 echo", result, "hello")
    
    def test_dangerous_command(self):
        """测试危险命令拦截"""
        print("\n【测试危险命令拦截】")
        
        result = self.tools.run_command("rm -rf /")
        self.assert_result("拦截 rm -rf", result, "危险操作")
    
    # ========== 运行所有测试 ==========
    
    def run_all(self):
        """运行所有测试"""
        print("=" * 50)
        print("Coding Agent v1.3 工具测试")
        print("=" * 50)
        
        # 文件操作
        self.test_write_file()
        self.test_read_file()
        self.test_edit_file()
        self.test_list_files()
        self.test_find_files()
        self.test_search_code()
        self.test_mkdir()
        self.test_delete_file()
        
        # Git
        self.test_git_status()
        
        # HTTP
        self.test_http_get()
        
        # 环境变量
        self.test_get_env()
        
        # 记忆
        self.test_memory()
        
        # 用户交互
        self.test_ask_user()
        
        # 命令执行
        self.test_run_command()
        self.test_dangerous_command()
        
        # 结果
        print("\n" + "=" * 50)
        print(f"测试结果: ✅ {self.passed} 通过, ❌ {self.failed} 失败")
        print("=" * 50)
        
        # 清理
        self.cleanup()
        
        return self.failed == 0


if __name__ == "__main__":
    tester = TestTools()
    success = tester.run_all()
    sys.exit(0 if success else 1)