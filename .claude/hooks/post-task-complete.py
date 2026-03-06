#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostToolUse Hook - 任务完成桌面通知

【功能概述】
本钩子在工具执行完成后发送桌面通知，提供以下功能：
1. 跨平台桌面通知支持（Windows/macOS/Linux）
2. 可配置的工具过滤（只对特定工具发送通知）
3. 操作结果记录到日志文件

【Hook 类型】
PostToolUse - 在工具执行后运行

【触发条件】
- 工具名称匹配配置列表（默认：Write, Edit, Bash）
- 触发时机：工具成功执行后

【支持平台】
- Windows: 使用 BurntToast 模块或 Windows 原生 Toast 通知
- macOS: 使用 osascript display notification
- Linux: 使用 notify-send 命令

【依赖说明】
- Windows: 推荐安装 BurntToast 模块
  PowerShell: Install-Module -Name BurntToast -Scope CurrentUser

【作者】
Claude Code Hook System

【版本】
1.0.0
"""
import sys
import json
import subprocess
import platform
import os
from datetime import datetime

# ============== 配置项 ==============
# 需要发送通知的工具列表
NOTIFY_TOOLS = {'Write', 'Edit', 'Bash', 'Task'}

# 是否启用通知（可设置为 False 禁用）
ENABLE_NOTIFICATION = True
# ====================================


def send_notification_macos(title: str, message: str) -> None:
    """在 macOS 系统上发送桌面通知"""
    subprocess.run([
        'osascript', '-e',
        f'display notification "{message}" with title "{title}"'
    ], capture_output=True)


def send_notification_linux(title: str, message: str) -> None:
    """在 Linux 系统上发送桌面通知"""
    subprocess.run(['notify-send', title, message], capture_output=True)


def send_notification_windows_burnttoast(title: str, message: str) -> bool:
    """在 Windows 系统上使用 BurntToast 模块发送通知"""
    ps_cmd = f'New-BurntToastNotification -Text "{title}", "{message}"'
    result = subprocess.run(
        ['powershell', '-Command', ps_cmd],
        capture_output=True
    )
    return result.returncode == 0


def send_notification_windows_native(title: str, message: str) -> None:
    """在 Windows 系统上使用原生 Toast 通知（回退方案）"""
    ps_cmd = f'''
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
    $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
    $text = $xml.GetElementsByTagName("text")
    $text[0].AppendChild($xml.CreateTextNode("{title}")) | Out-Null
    $text[1].AppendChild($xml.CreateTextNode("{message}")) | Out-Null
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Claude Code").Show($toast)
    '''
    subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True)


def send_notification(title: str, message: str) -> None:
    """发送系统桌面通知（跨平台）"""
    system = platform.system()

    try:
        if system == 'Darwin':  # macOS
            send_notification_macos(title, message)
        elif system == 'Linux':
            send_notification_linux(title, message)
        elif system == 'Windows':
            # Windows: 优先尝试 BurntToast
            try:
                success = send_notification_windows_burnttoast(title, message)
                if not success:
                    raise Exception("BurntToast not available")
            except Exception:
                # 回退到原生 Toast 通知
                send_notification_windows_native(title, message)
    except Exception as e:
        print(f"[通知发送失败] {e}", file=sys.stderr)


def get_tool_description(tool_name: str, tool_input: dict) -> str:
    """
    根据工具类型生成描述信息

    Args:
        tool_name: 工具名称
        tool_input: 工具输入参数

    Returns:
        str: 工具描述信息
    """
    if tool_name == 'Write':
        file_path = tool_input.get('file_path', '')
        file_name = os.path.basename(file_path) if file_path else '未知文件'
        return f"写入文件: {file_name}"
    elif tool_name == 'Edit':
        file_path = tool_input.get('file_path', '')
        file_name = os.path.basename(file_path) if file_path else '未知文件'
        return f"编辑文件: {file_name}"
    elif tool_name == 'Bash':
        command = tool_input.get('command', '')
        # 截取命令前30个字符
        cmd_preview = command[:30] + '...' if len(command) > 30 else command
        return f"执行命令: {cmd_preview}"
    elif tool_name == 'Task':
        subagent_type = tool_input.get('subagent_type', '')
        description = tool_input.get('description', '')
        if description:
            return f"Agent任务: {subagent_type} - {description}"
        return f"Agent任务: {subagent_type}"
    else:
        return f"工具: {tool_name}"


def write_log(log_path: str, event: str, input_data: dict = None) -> None:
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tool_name = input_data.get('tool_name', '') if input_data else ''
    message = input_data.get('tool_input', {}) if input_data else {}
    log_entry = f"[{timestamp}] [{event}] tool={tool_name}, input={message}\n"

    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def main():
    """主函数"""
    # 日志文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    log_dir = os.path.join(project_root, 'hookslog')
    os.makedirs(log_dir, exist_ok=True)
    LOG_FILE = os.path.join(log_dir, 'post_task_complete.log')

    # 获取项目名称
    cwd = os.getcwd()
    project_name = os.path.basename(cwd) if cwd else 'Claude'

    # 记录启动
    write_log(LOG_FILE, "start")

    # 解析输入
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        write_log(LOG_FILE, "parse_error")
        return

    write_log(LOG_FILE, "parsed", input_data)

    # 提取字段
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    tool_result = input_data.get('tool_result', '')

    # 检查是否需要通知
    if tool_name not in NOTIFY_TOOLS:
        write_log(LOG_FILE, f"skip_{tool_name}", input_data)
        return

    # 检查是否启用通知
    if not ENABLE_NOTIFICATION:
        write_log(LOG_FILE, "disabled", input_data)
        return

    # 生成通知内容
    description = get_tool_description(tool_name, tool_input)
    title = f"[{project_name}] 任务完成"
    message = description

    # 发送通知
    write_log(LOG_FILE, "sending_notification", input_data)
    send_notification(title, message)
    write_log(LOG_FILE, "notification_sent", input_data)

    # 输出状态
    print(f"[TaskComplete] {description}", file=sys.stderr)


if __name__ == '__main__':
    main()