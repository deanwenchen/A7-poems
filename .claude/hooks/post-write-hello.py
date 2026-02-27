#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostToolUse Hook - Write 操作后执行的通知钩子

【功能概述】
本钩子在每次 Write 工具执行后自动触发，提供以下功能：
1. 在终端界面显示友好的文件保存确认消息
2. 将 Write 操作记录到日志文件，便于审计和追踪

【Hook 类型】
PostToolUse - 在工具执行后运行

【触发条件】
- 工具名称：Write
- 触发时机：Write 工具成功执行后

【CLI 调用示例】
# 模拟 Write 工具执行后的 Hook 调用
echo {"tool_name":"Write","tool_input":{"file_path":"D:/test.py"}} | python post-write-hello.py

【输入格式】
JSON 格式，通过 stdin 传入：
{
    "tool_name": "Write",           # 工具名称
    "tool_input": {
        "file_path": "D:/test.py"   # 被写入的文件路径
    }
}

【输出格式】
- stdout: 无（静默）
- stderr: 格式化的通知消息
- 退出码：0（成功）

【作者】
Claude Code Hook System

【版本】
1.0.0
"""
import sys
import json
from datetime import datetime


def parse_input() -> dict:
    """
    从标准输入解析 JSON 数据

    Returns:
        dict: 解析后的输入数据，包含 tool_name 和 tool_input
        None: 如果解析失败
    """
    try:
        input_data = json.loads(sys.stdin.read())
        return input_data
    except (json.JSONDecodeError, Exception):
        # JSON 解析失败或读取错误时返回 None
        return None


def format_notification_message(tool_name: str, file_path: str) -> str:
    """
    格式化通知消息，用于在终端显示

    Args:
        tool_name: 工具名称（如 Write、Edit 等）
        file_path: 被操作的文件路径

    Returns:
        str: 格式化后的消息字符串
    """
    separator = "=" * 50
    message = (
        f"\n{separator}\n"
        f"✅ Hook 触发成功！\n"
        f"📄 文件已保存：{file_path}\n"
        f"{separator}\n"
    )
    return message


def write_log(file_path: str, log_path: str) -> None:
    """
    将 Write 操作记录到日志文件

    Args:
        file_path: 被写入的文件路径
        log_path: 日志文件的完整路径

    Note:
        日志格式：[YYYY-MM-DD HH:MM:SS] Hook 被调用 - Write 操作：{文件路径}
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] Hook 被调用 - Write 操作：{file_path}\n"

    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def main():
    """
    主函数：处理 Write 工具执行后的钩子逻辑

    执行流程：
    1. 从 stdin 读取并解析 JSON 输入
    2. 提取工具名称和文件路径
    3. 如果是 Write 工具，执行以下操作：
       a. 在 stderr 输出格式化通知消息
       b. 将操作记录到日志文件
    4. 正常退出
    """
    # 配置项：日志文件路径（使用原始字符串避免转义）
    LOG_FILE = r"D:\Claude\PullRequest\post_write_hello.log"

    # 步骤 1: 解析输入数据
    input_data = parse_input()
    if input_data is None:
        # 输入解析失败，静默退出
        sys.exit(0)

    # 步骤 2: 提取关键字段
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    # 步骤 3: 只处理 Write 工具
    if tool_name != 'Write':
        sys.exit(0)

    # 步骤 4a: 在终端显示通知消息（输出到 stderr）
    # 使用 stderr 是因为这是诊断/通知信息，不应该与 stdout 的数据混合
    notification = format_notification_message(tool_name, file_path)
    print(notification, file=sys.stderr)

    # 步骤 4b: 写入日志文件，用于审计追踪
    write_log(file_path, LOG_FILE)

    # 正常退出
    sys.exit(0)


if __name__ == '__main__':
    main()
