#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UserPromptSubmit Hook - 用户提示词自动增强器

【功能概述】
本钩子在用户提交提示词后自动运行，检测特定类型的任务并追加相关规范，
提供以下功能：
1. 智能识别写作类任务
2. 自动注入写作规范到上下文中
3. 过滤简单回复和斜杠命令（不需要增强）

【Hook 类型】
UserPromptSubmit - 在用户提交提示词时运行

【触发条件】
- 用户输入包含写作相关关键词
- 输入长度 >= 5 字符
- 不是简单回复（如"好的"、"继续"等）
- 不是斜杠命令（如"/help"）

【增强规则】
写作任务关键词（满足任一即可）：
- 中文：写、文章、生成、创作
- 英文：write、article、内容

注入的写作规范：
1. 风格：接地气、说人话，避免 AI 腔
2. 结构：开头金句 -> 核心要点 -> 实战案例 -> 总结升华
3. 字数：1500-2000 字
4. 检查：完成后运行/pre-check 进行质量检查

【CLI 调用示例】
# 模拟写作任务（会触发增强）
echo {"prompt":"帮我写一篇文章"} | python user-prompt-enhance.py

# 模拟简单回复（不触发）
echo {"prompt":"好的"} | python user-prompt-enhance.py

# 模拟斜杠命令（不触发）
echo {"prompt":"/help"} | python user-prompt-enhance.py

【输入格式】
JSON 格式，通过 stdin 传入：
{
    "prompt": "帮我写一篇文章"    # 用户输入的提示词
}

【输出格式】
- stdout: 增强内容（当检测到写作任务时）
- stderr: Hook 状态信息
- 退出码：0（成功）

【注意事项】
1. 输入必须是有效的 JSON 格式
2. 简单回复和短输入会被过滤
3. 斜杠命令不会被增强

【作者】
Claude Code Hook System

【版本】
1.0.0
"""
import sys
import json
from datetime import datetime


# =============================================================================
# 配置区域
# =============================================================================

# 简单回复列表（不需要增强的短回复）
SIMPLE_RESPONSES = ['好的', '是的', '继续', 'ok', 'yes', 'no', '确认', '取消']

# 写作任务关键词列表
WRITING_KEYWORDS = ['写', '文章', '生成', '创作', 'write', 'article', '内容']

# 写作规范模板（当检测到写作任务时注入）
WRITING_SPEC_TEMPLATE = """
---
## 写作规范提醒（Hook 自动注入）
1. **风格**：接地气、说人话，避免 AI 腔
2. **结构**：开头金句 -> 核心要点 -> 实战案例 -> 总结升华
3. **字数**：1500-2000 字
4. **检查**：完成后运行 /pre-check 进行质量检查
---"""

# 日志文件路径
LOG_FILE = r"D:\Claude\PullRequest\user_prompt_enhance.log"


def parse_input() -> dict:
    """
    从标准输入解析 JSON 数据

    Returns:
        dict: 解析后的输入数据，包含 prompt 字段
        None: 如果解析失败
    """
    try:
        input_data = json.loads(sys.stdin.read())
        return input_data
    except json.JSONDecodeError:
        # JSON 解析失败
        return None


def is_simple_response(prompt: str) -> bool:
    """
    检查是否是简单回复（不需要增强）

    Args:
        prompt: 用户输入的提示词

    Returns:
        bool: 如果是简单回复返回 True，否则返回 False
    """
    # 检查是否在简单回复列表中
    if prompt.lower() in SIMPLE_RESPONSES:
        return True

    # 检查长度是否太短（少于 5 字符）
    if len(prompt) < 5:
        return True

    return False


def is_slash_command(prompt: str) -> bool:
    """
    检查是否是斜杠命令

    Args:
        prompt: 用户输入的提示词

    Returns:
        bool: 如果是斜杠命令返回 True，否则返回 False
    """
    return prompt.startswith('/')


def is_writing_task(prompt: str) -> bool:
    """
    检查是否是写作类任务

    Args:
        prompt: 用户输入的提示词

    Returns:
        bool: 如果是写作任务返回 True，否则返回 False

    检查逻辑：
        遍历写作关键词列表，如果 prompt 包含任一关键词则判定为写作任务
    """
    prompt_lower = prompt.lower()
    for keyword in WRITING_KEYWORDS:
        if keyword in prompt_lower:
            return True
    return False


def get_enhancement_content() -> str:
    """
    获取要注入的增强内容

    Returns:
        str: 写作规范模板字符串
    """
    return WRITING_SPEC_TEMPLATE


def write_log(input_data: dict, log_path: str, event: str = "call") -> None:
    """
    写入 Hook 调用日志

    Args:
        input_data: 完整的输入数据
        log_path: 日志文件路径
        event: 事件类型 (start/parse_error/no_prompt/simple_response/slash_command/enhancement_injected/exit)
    """
    with open(log_path, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        prompt = input_data.get('prompt', '') if input_data else ''
        f.write(f"[{timestamp}] [{event}] prompt={prompt[:50] if len(prompt) > 50 else prompt}\n")


def main():
    """
    主函数：处理用户提示词增强逻辑

    执行流程：
    1. 从 stdin 读取并解析 JSON 输入
    2. 获取用户提示词
    3. 过滤简单回复和短输入
    4. 过滤斜杠命令
    5. 检测是否是写作任务
    6. 如果是写作任务，输出增强内容到上下文
    7. 记录到日志文件
    """
    # 步骤 1: Hook 启动
    write_log({}, LOG_FILE, "start")

    # 步骤 2: 解析输入数据
    input_data = parse_input()
    if input_data is None:
        # JSON 解析失败，记录日志后退出
        write_log({}, LOG_FILE, "parse_error")
        sys.exit(0)

    # 步骤 3: 记录输入解析成功
    write_log(input_data, LOG_FILE, "parsed")

    # 步骤 4: 获取用户提示词
    user_input = input_data.get('prompt', '').strip()

    # 如果没有 prompt 字段，直接退出
    if not user_input:
        write_log(input_data, LOG_FILE, "no_prompt")
        sys.exit(0)

    # 步骤 5: 过滤简单回复
    if is_simple_response(user_input):
        # 不需要增强，记录日志后退出
        write_log(input_data, LOG_FILE, "simple_response")
        sys.exit(0)

    # 步骤 6: 过滤斜杠命令
    if is_slash_command(user_input):
        # 斜杠命令不需要增强
        write_log(input_data, LOG_FILE, "slash_command")
        sys.exit(0)

    # 步骤 7: 检测是否是写作任务
    if is_writing_task(user_input):
        # 步骤 8: 输出增强内容到 stdout（会添加到 AI 上下文中）
        enhancement = get_enhancement_content()
        print(enhancement)

        # 在 stderr 输出状态信息
        print(f"[Hook] 已为写作任务注入规范", file=sys.stderr)

        # 记录增强注入日志
        write_log(input_data, LOG_FILE, "enhancement_injected")
    else:
        # 非写作任务
        write_log(input_data, LOG_FILE, "not_writing_task")

    # 步骤 9: 记录到日志文件
    write_log(input_data, LOG_FILE, "exit")

    # 正常退出
    sys.exit(0)


if __name__ == '__main__':
    main()
