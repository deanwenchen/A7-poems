#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostToolUse Hook - 自动代码格式化

【功能概述】
本钩子在保存代码文件后自动运行对应语言的格式化工具，提供以下功能：
1. 支持多种编程语言的自动格式化
2. 智能排除不需要格式化的目录（如 node_modules、venv 等）
3. 异步执行格式化工具，不影响主流程

【Hook 类型】
PostToolUse - 在工具执行后运行

【触发条件】
- 工具名称：Write
- 文件扩展名：.py, .js, .ts, .jsx, .tsx, .json, .css, .go
- 文件不在排除目录中
- 触发时机：Write 工具执行后

【支持的格式化工具】
1. Python (.py): black
2. JavaScript/TypeScript (.js, .ts, .jsx, .tsx): prettier
3. JSON (.json): prettier
4. CSS (.css): prettier
5. Go (.go): gofmt

【排除的目录】
- node_modules - Node.js 依赖目录
- venv / .venv - Python 虚拟环境
- __pycache__ - Python 字节码缓存
- dist / build - 构建输出目录
- .git - Git 版本控制目录

【CLI 调用示例】
# 模拟 Python 文件写入（触发 black 格式化）
echo {"tool_name":"Write","tool_input":{"file_path":"src/app.py"}} | python post-auto-format.py

# 模拟 JS 文件写入（触发 prettier 格式化）
echo {"tool_name":"Write","tool_input":{"file_path":"src/index.js"}} | python post-auto-format.py

# 模拟非代码文件（不触发）
echo {"tool_name":"Write","tool_input":{"file_path":"README.md"}} | python post-auto-format.py

【输入格式】
JSON 格式，通过 stdin 传入：
{
    "tool_name": "Write",
    "tool_input": {
        "file_path": "src/app.py"
    }
}

【输出格式】
- stdout: 无（静默）
- stderr: 格式化状态信息
- 退出码：0（成功）

【依赖说明】
- Python: 需要安装 black (pip install black)
- JavaScript/TypeScript: 需要安装 prettier (npm install -g prettier)
- Go: 内置 gofmt 工具

【作者】
Claude Code Hook System

【版本】
1.0.0
"""
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime


# =============================================================================
# 配置区域
# =============================================================================

# 文件扩展名与格式化工具的映射
FORMATTERS = {
    '.js': 'npx prettier --write "{file}"',
    '.ts': 'npx prettier --write "{file}"',
    '.jsx': 'npx prettier --write "{file}"',
    '.tsx': 'npx prettier --write "{file}"',
    '.json': 'npx prettier --write "{file}"',
    '.css': 'npx prettier --write "{file}"',
    '.py': 'black "{file}"',
    '.go': 'gofmt -w "{file}"',
}

# 需要排除的目录（这些目录下的文件不会被格式化）
EXCLUDED_DIRS = {'node_modules', 'venv', '.venv', '__pycache__', 'dist', 'build', '.git'}

# 日志文件路径
LOG_FILE = r"D:\Claude\PullRequest\post_auto_format.log"


def is_excluded_path(file_path: str) -> bool:
    """
    检查文件路径是否在排除目录中

    Args:
        file_path: 文件路径

    Returns:
        bool: 如果在排除目录中返回 True，否则返回 False

    检查逻辑：
        遍历路径的每个部分，检查是否在 EXCLUDED_DIRS 集合中
    """
    path = Path(file_path)
    for part in path.parts:
        if part in EXCLUDED_DIRS:
            return True
    return False


def should_format(file_path: str) -> bool:
    """
    检查是否应该格式化该文件

    Args:
        file_path: 文件路径

    Returns:
        bool: 如果需要格式化返回 True，否则返回 False

    检查逻辑：
        1. 检查是否在排除目录中
        2. 检查文件扩展名是否在 FORMATTERS 字典中
    """
    # 检查是否在排除目录中
    if is_excluded_path(file_path):
        return False

    # 检查文件扩展名
    path = Path(file_path)
    return path.suffix in FORMATTERS


def run_formatter(file_path: str) -> str:
    """
    运行格式化工具

    Args:
        file_path: 文件路径

    Returns:
        str: 格式化结果状态信息

    可能的返回值：
        - "✅ 格式化成功" - 格式化成功
        - "⚠️ 格式化失败：xxx" - 格式化命令执行失败
        - "⚠️ 格式化超时" - 命令执行超时（30 秒）
        - "⚠️ 格式化工具未安装" - 格式化工具不存在
        - "⚠️ 格式化错误：xxx" - 其他异常
    """
    path = Path(file_path)
    suffix = path.suffix

    # 检查是否有对应的格式化工具
    if suffix not in FORMATTERS:
        return None

    # 构建命令
    cmd = FORMATTERS[suffix].format(file=file_path)

    try:
        # 执行格式化命令
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 30 秒超时
        )

        if result.returncode == 0:
            return "✅ 格式化成功"
        else:
            # 返回错误信息（截取前 100 字符）
            error_msg = result.stderr[:100] if result.stderr else result.stdout[:100]
            return f"⚠️ 格式化失败：{error_msg}"

    except subprocess.TimeoutExpired:
        return "⚠️ 格式化超时"
    except FileNotFoundError:
        return "⚠️ 格式化工具未安装"
    except Exception as e:
        return f"⚠️ 格式化错误：{str(e)}"


def write_log(input_data: dict, log_path: str, event: str = "call") -> None:
    """
    写入 Hook 调用日志

    Args:
        input_data: 完整的输入数据
        log_path: 日志文件路径
        event: 事件类型 (start/parse_error/tool_mismatch/not_format_needed/formatting/format_success/format_failed/exit)
    """
    with open(log_path, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tool_name = input_data.get('tool_name', 'Unknown') if input_data else 'Unknown'
        tool_input = input_data.get('tool_input', {}) if input_data else {}
        file_path = tool_input.get('file_path', '')
        f.write(f"[{timestamp}] [{event}] {tool_name}: file_path={file_path}\n")


def main():
    """
    主函数：处理自动代码格式化逻辑

    执行流程：
    1. 从 stdin 读取并解析 JSON 输入
    2. 检查是否为 Write 工具
    3. 检查文件是否需要格式化
    4. 运行对应的格式化工具
    5. 输出格式化状态
    6. 记录到日志文件
    """
    # 配置项：日志文件路径
    LOG_FILE = r"D:\Claude\PullRequest\post_auto_format.log"

    # 步骤 1: Hook 启动
    write_log({}, LOG_FILE, "start")

    # 步骤 2: 解析输入数据
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # JSON 解析失败，记录日志后退出
        write_log({}, LOG_FILE, "parse_error")
        return

    # 步骤 3: 记录输入解析成功
    write_log(input_data, LOG_FILE, "parsed")

    # 步骤 4: 提取字段
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    # 步骤 5: 只处理 Write 工具
    if tool_name != 'Write':
        write_log(input_data, LOG_FILE, "tool_mismatch")
        return

    # 步骤 6: 检查是否需要格式化
    if not file_path or not should_format(file_path):
        write_log(input_data, LOG_FILE, "not_format_needed")
        return

    # 步骤 7: 运行格式化工具
    write_log(input_data, LOG_FILE, "formatting")
    result = run_formatter(file_path)

    # 步骤 8: 输出状态信息（如果有返回值）
    if result:
        file_name = Path(file_path).name
        print(f"\n[AutoFormat] {file_name}: {result}", file=sys.stderr)
        # 记录格式化结果
        if "成功" in result:
            write_log(input_data, LOG_FILE, "format_success")
        else:
            write_log(input_data, LOG_FILE, "format_failed")

    # 步骤 9: 记录到日志文件
    write_log(input_data, LOG_FILE, "exit")


if __name__ == '__main__':
    main()
