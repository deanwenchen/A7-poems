#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SessionStart Hook - 环境检查

【功能概述】
本钩子在 Claude Code 会话启动时自动运行，检查必需的工具和依赖是否已安装。
提供以下功能：
1. 检测必需工具是否可用（Node.js、Python、Git）
2. 检测可选但推荐的工具（Prettier、Black）
3. 输出友好的检查结果报告
4. 记录检查结果到日志文件

【Hook 类型】
SessionStart - 在会话启动时运行

【触发条件】
- Claude Code 会话启动时自动触发
- 无需用户交互

【CLI 调用示例】
# 直接运行（模拟会话启动）
python session-start-check.py

# 或通过 stdin 传入空 JSON
echo {} | python session-start-check.py

【输入格式】
无输入或空 JSON（SessionStart hook 通常不需要输入）

【输出格式】
- stdout: 无（静默）
- stderr: 格式化的检查结果报告
- 退出码：0（成功，即使缺少工具也不阻塞）

【注意事项】
1. 缺少必需工具会显示警告，但不会阻塞会话
2. 缺少可选工具仅显示建议信息
3. 日志记录在项目根目录的 hookslog 文件夹中

【作者】
Claude Code Hook System

【版本】
1.0.0
"""
import sys
import shutil
import os
from datetime import datetime


# =============================================================================
# 配置区域
# =============================================================================

# 检查必需的工具
REQUIRED_TOOLS = {
    'node': 'Node.js (npm install)',
    'python': 'Python 3.x',
    'git': 'Git版本控制',
}

# 可选但推荐的工具
OPTIONAL_TOOLS = {
    'prettier': 'Prettier代码格式化 (npm install -g prettier)',
    'black': 'Black Python格式化 (pip install black)',
}

# 日志文件路径（项目根目录下的 hookslog 文件夹）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
LOG_DIR = os.path.join(PROJECT_ROOT, 'hookslog')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'session_start_check.log')


# =============================================================================
# 工具函数
# =============================================================================

def check_tool(tool_name: str) -> bool:
    """
    检查指定工具是否可用

    Args:
        tool_name: 工具名称（如 'node', 'python' 等）

    Returns:
        bool: 如果工具可用返回 True，否则返回 False
    """
    return shutil.which(tool_name) is not None


def write_log(log_path: str, event: str, details: str = "") -> None:
    """
    写入 Hook 运行日志

    Args:
        log_path: 日志文件路径
        event: 事件类型 (start/check_result/exit)
        details: 详细信息
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{event}] {details}\n"

    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def format_check_result(missing_required: list, missing_optional: list) -> str:
    """
    格式化检查结果报告

    Args:
        missing_required: 缺少的必需工具列表
        missing_optional: 缺少的可选工具列表

    Returns:
        str: 格式化后的报告字符串
    """
    separator = "=" * 50

    if not missing_required and not missing_optional:
        return f"\n{separator}\n✅ 环境检查通过，所有工具已就绪\n{separator}\n"

    lines = [f"\n{separator}", "环境检查结果", separator]

    if missing_required:
        lines.append("\n❌ 缺少必需工具（请安装）：")
        for item in missing_required:
            lines.append(item)

    if missing_optional:
        lines.append("\n⚠️ 缺少可选工具（建议安装）：")
        for item in missing_optional:
            lines.append(item)

    lines.append(f"\n{separator}\n")
    return "\n".join(lines)


# =============================================================================
# 主函数
# =============================================================================

def main():
    """
    主函数：执行环境检查

    执行流程：
    1. 记录 Hook 启动日志
    2. 检查必需工具
    3. 检查可选工具
    4. 输出检查结果到 stderr
    5. 记录检查结果到日志文件
    6. 正常退出
    """
    # 步骤 1: Hook 启动，记录启动日志
    write_log(LOG_FILE, "start", "SessionStart hook triggered")

    missing_required = []
    missing_optional = []

    # 步骤 2: 检查必需工具
    for tool, desc in REQUIRED_TOOLS.items():
        if not check_tool(tool):
            missing_required.append(f"  ❌ {tool}: {desc}")
        else:
            # 记录已安装的工具
            write_log(LOG_FILE, "tool_found", f"{tool}: OK")

    # 步骤 3: 检查可选工具
    for tool, desc in OPTIONAL_TOOLS.items():
        if not check_tool(tool):
            missing_optional.append(f"  ⚠️ {tool}: {desc}")

    # 步骤 4: 输出检查结果到 stderr
    report = format_check_result(missing_required, missing_optional)
    print(report, file=sys.stderr)

    # 步骤 5: 记录检查结果到日志文件
    result_summary = f"required_missing={len(missing_required)}, optional_missing={len(missing_optional)}"
    write_log(LOG_FILE, "check_result", result_summary)

    # 步骤 6: 记录退出日志
    write_log(LOG_FILE, "exit", "SessionStart hook completed")

    # 正常退出（即使缺少工具也不阻塞会话）
    sys.exit(0)


if __name__ == '__main__':
    main()