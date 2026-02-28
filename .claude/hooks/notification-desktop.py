#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostToolUse Hook - 桌面通知转发器

【功能概述】
本钩子将 Claude 的通知消息转发到操作系统桌面通知，提供以下功能：
1. 跨平台桌面通知支持（Windows/macOS/Linux）
2. 自动检测操作系统并选择合适的通知方式
3. Windows 平台支持两种通知方式（BurntToast 模块和原生 Toast）

【Hook 类型】
PostToolUse - 在工具执行后运行

【触发条件】
- 输入包含 message 字段
- 触发时机：相关工具执行后

【支持平台】
- Windows: 使用 BurntToast 模块或 Windows 原生 Toast 通知
- macOS: 使用 osascript display notification
- Linux: 使用 notify-send 命令

【CLI 调用示例】
# 发送桌面通知
echo {"message":"任务完成！","session_id":"test123"} | python notification-desktop.py

【输入格式】
JSON 格式，通过 stdin 传入：
{
    "message": "任务完成！",      # 通知消息内容
    "session_id": "test123"      # 会话 ID（可选）
}

【输出格式】
- stdout: 无（静默）
- stderr: 通知发送状态信息
- 退出码：0（成功）

【依赖说明】
- Windows: 推荐安装 BurntToast 模块
  PowerShell: Install-Module -Name BurntToast -Scope CurrentUser
- Linux: 需要安装 libnotify-bin
  Ubuntu/Debian: sudo apt-get install libnotify-bin
- macOS: 无需额外依赖（使用系统自带 osascript）

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


def send_notification_macos(title: str, message: str) -> None:
    """
    在 macOS 系统上发送桌面通知

    使用 AppleScript 的 display notification 命令

    Args:
        title: 通知标题
        message: 通知消息内容
    """
    subprocess.run([
        'osascript', '-e',
        f'display notification "{message}" with title "{title}"'
    ])


def send_notification_linux(title: str, message: str) -> None:
    """
    在 Linux 系统上发送桌面通知

    使用 notify-send 命令（需要安装 libnotify-bin）

    Args:
        title: 通知标题
        message: 通知消息内容
    """
    subprocess.run(['notify-send', title, message])


def send_notification_windows_burnttoast(title: str, message: str) -> bool:
    """
    在 Windows 系统上使用 BurntToast 模块发送通知

    BurntToast 是 PowerShell 的通知模块，需要先安装：
    Install-Module -Name BurntToast -Scope CurrentUser

    Args:
        title: 通知标题
        message: 通知消息内容

    Returns:
        bool: 发送成功返回 True，失败返回 False
    """
    ps_cmd = f'New-BurntToastNotification -Text "{title}", "{message}"'
    result = subprocess.run(
        ['powershell', '-Command', ps_cmd],
        capture_output=True
    )
    return result.returncode == 0


def send_notification_windows_native(title: str, message: str) -> None:
    """
    在 Windows 系统上使用原生 Toast 通知（回退方案）

    使用 Windows.UI.Notifications 命名空间直接创建 Toast 通知

    Args:
        title: 通知标题
        message: 通知消息内容
    """
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
    """
    发送系统桌面通知（跨平台）

    根据操作系统自动选择合适的通知方式：
    - macOS: osascript
    - Linux: notify-send
    - Windows: BurntToast（优先）或原生 Toast（回退）

    Args:
        title: 通知标题
        message: 通知消息内容

    Note:
        Windows 平台优先使用 BurntToast，如果失败则回退到原生 Toast 通知
    """
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
        print(f"通知发送失败：{e}", file=sys.stderr)


def log_notification(input_data: dict, log_path: str, event: str = "call") -> None:
    """
    记录通知发送日志

    Args:
        input_data: 完整的输入数据
        log_path: 日志文件路径
        event: 事件类型 (start/parse_error/no_message/sending_notification/notification_sent/exit)
    """
    with open(log_path, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = input_data.get('message', '') if input_data else ''
        session_id = input_data.get('session_id', '') if input_data else ''
        f.write(f"[{timestamp}] [{event}] message={message[:50] if len(message) > 50 else message}, session_id={session_id}\n")


def main():
    """
    主函数：处理桌面通知转发逻辑

    执行流程：
    1. 从 stdin 读取并解析 JSON 输入
    2. 提取 message 和 session_id 字段
    3. 构建通知标题
    4. 调用系统通知 API 发送桌面通知
    5. 记录到日志文件
    """
    # 配置项：日志文件路径
    LOG_FILE = r"D:\Claude\PullRequest\notification_desktop.log"

    # 步骤 1: Hook 启动
    log_notification({}, LOG_FILE, "start")

    # 步骤 2: 解析输入数据
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # JSON 解析失败，记录日志后退出
        log_notification({}, LOG_FILE, "parse_error")
        return

    # 步骤 3: 记录输入解析成功
    log_notification(input_data, LOG_FILE, "parsed")

    # 步骤 4: 提取字段
    message = input_data.get('message', '')
    session_id = input_data.get('session_id', '')

    # 获取工作目录作为会话标识（区分不同 Claude 窗口）
    cwd = os.getcwd()
    # 取最后一级目录名作为标识
    project_name = os.path.basename(cwd) if cwd else 'unknown'

    # 步骤 5: 如果没有消息内容，直接退出
    if not message:
        log_notification(input_data, LOG_FILE, "no_message")
        return

    # 步骤 6: 构建通知标题（用 [] 包裹项目名）
    title = f"[{project_name}] {message[:30]}" if len(message) > 30 else f"[{project_name}] {message}"

    # 步骤 7: 发送桌面通知（标题包含项目名，内容是完整消息）
    log_notification(input_data, LOG_FILE, "sending_notification")
    send_notification(title, message)

    # 步骤 8: 在 stderr 输出状态信息
    message_preview = message[:50] if len(message) > 50 else message
    print(f"[Notification] 已发送桌面通知：{message_preview}...", file=sys.stderr)

    # 步骤 9: 记录到日志文件
    log_notification(input_data, LOG_FILE, "notification_sent")

    log_notification(input_data, LOG_FILE, "exit")


if __name__ == '__main__':
    main()
