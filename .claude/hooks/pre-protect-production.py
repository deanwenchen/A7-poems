#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PreToolUse Hook - 保护 Production 目录

【功能概述】
本钩子在尝试修改 production/prod/.env目录下的文件前自动拦截，提供以下功能：
1. 保护生产环境配置文件不被意外修改
2. 支持多个受保护目录路径
3. 兼容 Windows 和 Unix 路径格式

【Hook 类型】
PreToolUse - 在工具执行前运行，可拦截操作

【触发条件】
- 工具名称：Write 或 Edit
- 文件路径包含受保护目录
- 触发时机：Write/Edit 工具执行前

【受保护目录】
- production/ - 生产环境目录
- prod/ - 生产环境缩写目录
- .env - 环境变量文件

【CLI 调用示例】
# 模拟尝试修改 production 目录（会被拦截）
echo {"tool_name":"Write","tool_input":{"file_path":"production/config.json"}} | python pre-protect-production.py

# 模拟正常文件写入（放行）
echo {"tool_name":"Write","tool_input":{"file_path":"src/app.py"}} | python pre-protect-production.py

【输入格式】
JSON 格式，通过 stdin 传入：
{
    "tool_name": "Write",
    "tool_input": {
        "file_path": "production/config.json"
    }
}

【输出格式】
- stdout: JSON 格式的拒绝决策（当路径受保护时）
- stderr: 无
- 退出码：0（允许执行或已拒绝）

【决策说明】
当检测到受保护路径时，输出 JSON 决策：
{
    "decision": "deny",
    "message": "拒绝原因和详细信息"
}

【作者】
Claude Code Hook System

【版本】
1.0.0
"""
import sys
import io
import json
from datetime import datetime


# =============================================================================
# 配置区域
# =============================================================================

# 受保护的目录列表（路径中包含这些目录名的文件都会被保护）
PROTECTED_DIRS = ['production/', 'prod/', '.env']

# 日志文件路径
LOG_FILE = r"D:\Claude\PullRequest\pre_protect_production.log"


def normalize_path(file_path: str) -> str:
    """
    规范化文件路径（统一使用正斜杠）

    Args:
        file_path: 原始文件路径

    Returns:
        str: 规范化后的路径（所有反斜杠替换为正斜杠）

    Note:
        Windows 路径使用反斜杠 (\\)，Unix 路径使用正斜杠 (/)
        此函数统一转换为正斜杠格式，便于后续匹配
    """
    return file_path.replace('\\', '/')


def is_protected_path(file_path: str) -> tuple:
    """
    检查文件路径是否在受保护目录中

    Args:
        file_path: 文件路径

    Returns:
        tuple: (is_protected, protected_dir)
            - is_protected: bool，是否受保护
            - protected_dir: str，匹配的受保护目录名，如果没有匹配则返回空字符串
    """
    # 规范化路径
    path_normalized = normalize_path(file_path)

    # 逐个检查是否在保护列表中
    for protected_dir in PROTECTED_DIRS:
        if protected_dir in path_normalized:
            return True, protected_dir

    return False, ''


def create_deny_decision(file_path: str, protected_dir: str) -> dict:
    """
    创建拒绝执行的决策对象

    Args:
        file_path: 被拦截的文件路径
        protected_dir: 匹配的受保护目录名

    Returns:
        dict: 包含 decision 和 message 的决策对象
    """
    decision = {
        "decision": "deny",
        "message": f"❌ 禁止修改受保护的路径！\n路径：{file_path}\n原因：包含受保护目录 '{protected_dir}'\n\n请先切换到 dev 环境或手动操作。"
    }
    return decision


def write_log(file_path: str, log_path: str) -> None:
    """
    写入 Hook 调用日志

    Args:
        file_path: 被拦截的文件路径
        log_path: 日志文件路径
    """
    with open(log_path, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] Hook 被调用 - Write 操作：{file_path}\n")


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
    主函数：处理保护 Production 目录的拦截逻辑

    执行流程：
    1. 设置 UTF-8 编码输出
    2. 从 stdin 读取并解析 JSON 输入
    3. 提取工具名称和文件路径
    4. 只检查 Write 和 Edit 工具
    5. 检查文件路径是否在受保护目录中
    6. 如果受保护，输出拒绝决策；否则允许执行
    7. 记录到日志文件
    """
    # 步骤 1: 设置 UTF-8 编码输出
    setup_utf8_output()

    # 步骤 2: 解析输入数据
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # JSON 解析失败，静默退出（允许执行）
        sys.exit(0)

    # 步骤 3: 提取字段
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    # 步骤 4: 只检查 Write 和 Edit 工具
    if tool_name not in ['Write', 'Edit']:
        sys.exit(0)

    # 步骤 5: 检查是否是受保护路径
    is_protected, protected_dir = is_protected_path(file_path)

    if is_protected:
        # 步骤 6a: 输出拒绝决策
        decision = create_deny_decision(file_path, protected_dir)
        print(json.dumps(decision, ensure_ascii=False))
        sys.exit(0)

    # 步骤 6b: 允许执行（静默退出）
    # 记录到日志文件
    write_log(file_path, LOG_FILE)

    sys.exit(0)


if __name__ == '__main__':
    main()
