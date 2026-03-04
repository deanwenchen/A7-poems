#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PreToolUse Hook - 拦截危险命令

【功能概述】
本钩子在尝试执行 Bash 命令前自动检测并拦截危险操作，提供以下功能：
1. 检测并阻止 rm -rf 等破坏性命令
2. 检测 Fork 炸弹
3. 检测磁盘格式化命令
4. 检测危险权限修改命令

【Hook 类型】
PreToolUse - 在工具执行前运行，可拦截操作

【触发条件】
- 工具名称：Bash
- 命令匹配危险模式
- 触发时机：Bash 工具执行前

【拦截的命令模式】
1. rm -rf 系列：
   - rm -rf /          (删除根目录)
   - rm -rf ~          (删除用户主目录)
   - rm -rf *          (删除当前目录所有文件)
   - rm -rf ..         (删除父目录)

2. Fork 炸弹：
   - :(){ :|:& };:     (经典的 Bash Fork 炸弹)

3. 磁盘格式化：
   - mkfs.*            (格式化文件系统)

4. 磁盘覆盖：
   - dd if=...of=/dev/*  (写入原始设备)
   - > /dev/sda*         (重定向输出到磁盘)

5. 危险权限：
   - chmod -R 777 /    (递归设置根目录为完全开放权限)

【CLI 调用示例】
# 模拟危险命令（会被拦截）
echo {"tool_name":"Bash","tool_input":{"command":"rm -rf /"}} | python pre-block-dangerous-cmd.py

# 模拟安全命令（放行）
echo {"tool_name":"Bash","tool_input":{"command":"ls -la"}} | python pre-block-dangerous-cmd.py

【输入格式】
JSON 格式，通过 stdin 传入：
{
    "tool_name": "Bash",
    "tool_input": {
        "command": "rm -rf /"
    }
}

【输出格式】
- stdout: JSON 格式的拒绝决策（当检测到危险命令时）
- stderr: 无
- 退出码：0（允许执行或已拦截）

【决策说明】
当检测到危险命令时，输出 JSON 决策：
{
    "decision": "deny",
    "message": "拦截原因和详细信息"
}

【作者】
Claude Code Hook System

【版本】
1.0.0
"""
import sys
import io
import json
import re
import os
from datetime import datetime


# =============================================================================
# 配置区域
# =============================================================================

# 危险命令正则模式列表
DANGEROUS_PATTERNS = [
    # rm -rf / - 删除根目录
    r'rm\s+-rf\s+/',
    # rm -rf ~ - 删除用户主目录
    r'rm\s+-rf\s+~',
    # rm -rf * - 删除当前目录所有文件
    r'rm\s+-rf\s+\*',
    # rm -rf .. - 删除父目录
    r'rm\s+-rf\s+\.\.',
    # Fork 炸弹 - 经典的 Bash 自复制攻击
    r':()\s*{\s*:\|:&\s*};:',
    # mkfs.* - 格式化磁盘分区
    r'mkfs\.',
    # dd if=...of=/dev/... - 写入原始磁盘设备
    r'dd\s+if=.+of=/dev/',
    # > /dev/sda* - 重定向输出到磁盘
    r'>\s*/dev/sda',
    # chmod -R 777 / - 递归设置根目录为完全开放权限
    r'chmod\s+-R\s+777\s+/',
]

# 日志文件路径（项目根目录下的 hookslog 文件夹）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
LOG_DIR = os.path.join(PROJECT_ROOT, 'hookslog')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'pre_block_dangerous_cmd.log')


def normalize_command(command: str) -> str:
    """
    规范化命令字符串（可选的预处理步骤）

    Args:
        command: 原始命令字符串

    Returns:
        str: 规范化后的命令（目前直接返回原命令）

    Note:
        当前实现直接返回原命令，预留用于未来扩展
        可能的扩展：移除多余空格、统一大小写等
    """
    return command


def check_dangerous_pattern(command: str) -> tuple:
    """
    检查命令是否匹配危险模式

    Args:
        command: 要检查的命令字符串

    Returns:
        tuple: (is_dangerous, matched_pattern)
            - is_dangerous: bool，是否检测到危险模式
            - matched_pattern: str，匹配的危险模式，如果没有匹配则返回 None
    """
    for pattern in DANGEROUS_PATTERNS:
        # 使用 IGNORECASE 标志进行不区分大小写的匹配
        if re.search(pattern, command, re.IGNORECASE):
            return True, pattern
    return False, None


def create_deny_decision(command: str, pattern: str) -> dict:
    """
    创建拒绝执行的决策对象

    Args:
        command: 被拦截的命令
        pattern: 匹配的危险模式

    Returns:
        dict: 包含 decision 和 message 的决策对象
    """
    decision = {
        "decision": "deny",
        "message": f"🚨 危险命令已拦截！\n\n命令：{command}\n\n匹配的危险模式：{pattern}\n\n如果确实需要执行，请在终端手动运行。"
    }
    return decision


def write_log(input_data: dict, log_path: str, event: str = "call") -> None:
    """
    写入 Hook 调用日志

    Args:
        input_data: 完整的输入数据
        log_path: 日志文件路径
        event: 事件类型 (start/parse_error/tool_mismatch/dangerous_detected/dangerous_allowed/exit)
    """
    with open(log_path, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tool_name = input_data.get('tool_name', 'Unknown') if input_data else 'Unknown'
        tool_input = input_data.get('tool_input', {}) if input_data else {}
        f.write(f"[{timestamp}] [{event}] {tool_name}: {tool_input}\n")


def setup_utf8_output():
    """
    设置 UTF-8 编码输出（Windows 兼容）

    Note:
        Windows 系统默认编码可能是 GBK，需要显式设置为 UTF-8
        确保 JSON 输出中的中文字符正确显示
    """
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def main():
    """
    主函数：处理危险命令拦截逻辑

    执行流程：
    1. 设置 UTF-8 编码输出
    2. 从 stdin 读取并解析 JSON 输入
    3. 提取工具名称和命令
    4. 只检查 Bash 工具
    5. 检查命令是否匹配危险模式
    6. 如果危险，输出拒绝决策；否则允许执行
    7. 记录到日志文件
    """
    # 步骤 1: Hook 启动
    write_log({}, LOG_FILE, "start")

    # 步骤 2: 设置 UTF-8 编码输出
    setup_utf8_output()

    # 步骤 3: 解析输入数据
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # JSON 解析失败，记录日志后退出（允许执行）
        write_log({}, LOG_FILE, "parse_error")
        sys.exit(0)

    # 步骤 4: 记录输入解析成功
    write_log(input_data, LOG_FILE, "parsed")

    # 步骤 5: 提取字段
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    command = tool_input.get('command', '')

    # 步骤 6: 只检查 Bash 工具
    if tool_name != 'Bash':
        write_log(input_data, LOG_FILE, "tool_mismatch")
        sys.exit(0)

    # 步骤 7: 检查是否匹配危险模式
    is_dangerous, matched_pattern = check_dangerous_pattern(command)

    if is_dangerous:
        # 步骤 8a: 输出拒绝决策
        write_log(input_data, LOG_FILE, "dangerous_detected")
        decision = create_deny_decision(command, matched_pattern)
        print(json.dumps(decision, ensure_ascii=False))
        sys.exit(0)

    # 步骤 8b: 允许执行（静默退出）
    write_log(input_data, LOG_FILE, "command_allowed")

    sys.exit(0)


if __name__ == '__main__':
    main()
