#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostToolUse Hook - 自动备份

【功能概述】
本钩子在编辑重要文件后自动创建备份副本，提供以下功能：
1. 监控指定目录下的文件修改
2. 自动创建带时间戳的备份文件
3. 保留原始文件的所有属性（使用 copy2）

【Hook 类型】
PostToolUse - 在工具执行后运行

【触发条件】
- 工具名称：Edit
- 文件在指定备份目录中
- 文件存在
- 触发时机：Edit 工具执行后

【备份目录】
- config - 配置文件目录
- src - 源代码目录
- docs - 文档目录
- .claude - Claude 配置目录

【备份文件名格式】
{原文件名}.{YYYYMMDD_HHMMSS}.bak

示例：config/settings.json.20240115_143022.bak

【CLI 调用示例】
# 模拟 config 目录下的 Edit 操作（触发备份）
echo {"tool_name":"Edit","tool_input":{"file_path":"config/settings.json"}} | python post-auto-backup.py

# 模拟非备份目录（不触发）
echo {"tool_name":"Edit","tool_input":{"file_path":"temp.txt"}} | python post-auto-backup.py

# 模拟 Write 操作（不触发，只响应 Edit）
echo {"tool_name":"Write","tool_input":{"file_path":"config/settings.json"}} | python post-auto-backup.py

【输入格式】
JSON 格式，通过 stdin 传入：
{
    "tool_name": "Edit",
    "tool_input": {
        "file_path": "config/settings.json"
    }
}

【输出格式】
- stdout: 无（静默）
- stderr: 备份状态信息
- 退出码：0（成功）

【备份说明】
- 使用 shutil.copy2 保留文件元数据（修改时间、权限等）
- 备份文件与原文件在同一目录
- 每次编辑都会创建新的备份，不会覆盖旧备份

【作者】
Claude Code Hook System

【版本】
1.0.0
"""
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime


# =============================================================================
# 配置区域
# =============================================================================

# 需要备份的目录列表（文件路径中包含这些目录名就会触发备份）
BACKUP_DIRS = ['config', 'src', 'docs', '.claude']

# 日志文件路径
LOG_FILE = r"D:\Claude\PullRequest\post_auto_backup.log"


def is_in_backup_dir(file_path: str) -> bool:
    """
    检查文件是否在需要备份的目录中

    Args:
        file_path: 文件路径

    Returns:
        bool: 如果在备份目录中返回 True，否则返回 False

    检查逻辑：
        遍历 BACKUP_DIRS 列表，检查是否有任一目录名在文件路径中
    """
    for dir_name in BACKUP_DIRS:
        if dir_name in file_path:
            return True
    return False


def generate_backup_path(file_path: str, timestamp: str) -> str:
    """
    生成备份文件路径

    Args:
        file_path: 原始文件路径
        timestamp: 时间戳字符串（格式：YYYYMMDD_HHMMSS）

    Returns:
        str: 备份文件完整路径

    备份文件名格式：
        {原文件路径}.{timestamp}.bak

    示例：
        config/settings.json -> config/settings.json.20240115_143022.bak
    """
    return f"{file_path}.{timestamp}.bak"


def create_backup(file_path: str) -> tuple:
    """
    创建文件备份

    Args:
        file_path: 要备份的文件路径

    Returns:
        tuple: (success, message)
            - success: bool，是否备份成功
            - message: str，备份结果信息

    备份说明：
        - 使用 shutil.copy2 保留文件元数据
        - 备份文件名包含时间戳
    """
    # 生成时间戳
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 生成备份路径
    backup_path = generate_backup_path(file_path, timestamp)

    try:
        # 复制文件（copy2 保留元数据）
        shutil.copy2(file_path, backup_path)

        # 返回成功消息
        backup_filename = Path(backup_path).name
        return True, f"✅ 已创建备份：{backup_filename}"

    except Exception as e:
        # 返回错误消息
        return False, f"⚠️ 备份失败：{e}"


def write_log(file_path: str, log_path: str) -> None:
    """
    写入 Hook 调用日志

    Args:
        file_path: 被备份的文件路径
        log_path: 日志文件路径
    """
    with open(log_path, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] Hook 被调用 - Write 操作：{file_path}\n")


def main():
    """
    主函数：处理自动备份逻辑

    执行流程：
    1. 从 stdin 读取并解析 JSON 输入
    2. 检查是否为 Edit 工具
    3. 检查文件是否在备份目录中
    4. 如果满足条件，创建备份
    5. 输出备份状态
    6. 记录到日志文件
    """
    # 步骤 1: 解析输入数据
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # JSON 解析失败，静默退出
        return

    # 步骤 2: 提取字段
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    # 步骤 3: 只处理 Edit 工具
    if tool_name != 'Edit':
        return

    # 步骤 4: 检查是否在需要备份的目录中
    should_backup = is_in_backup_dir(file_path)

    if should_backup and Path(file_path).exists():
        # 步骤 5: 创建备份
        success, message = create_backup(file_path)

        # 步骤 6: 输出状态信息到 stderr
        if success:
            print(f"[Backup] {message}", file=sys.stderr)
        else:
            print(f"[Backup] {message}", file=sys.stderr)

    # 步骤 7: 记录到日志文件
    write_log(file_path, LOG_FILE)


if __name__ == '__main__':
    main()
