#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostToolUse Hook - 文章质量检查器

【功能概述】
本钩子在保存 Markdown 文件后自动触发，对文章内容进行质量检查，提供以下功能：
1. 统计文章基本指标（字符数、词数、标题、段落数）
2. 根据预设标准评估文章质量
3. 生成改进建议报告

【Hook 类型】
PostToolUse - 在工具执行后运行

【触发条件】
- 工具名称：Write
- 文件扩展名：.md（Markdown 文件）
- 触发时机：Write 工具成功执行后

【检查项目】
1. 字符数检查：建议至少 500 字符
2. 标题检查：必须包含一级标题（# 开头）
3. 段落数检查：建议至少 3 个段落以保证可读性

【CLI 调用示例】
# 模拟 Markdown 文件写入（触发质量检查）
echo {"tool_name":"Write","tool_input":{"file_path":"docs/article.md"}} | python post-article-quality.py

# 模拟非 Markdown 文件（不触发）
echo {"tool_name":"Write","tool_input":{"file_path":"src/app.py"}} | python post-article-quality.py

【输入格式】
JSON 格式，通过 stdin 传入：
{
    "tool_name": "Write",
    "tool_input": {
        "file_path": "docs/article.md"
    }
}

【输出格式】
- stdout: 无（静默）
- stderr: 文章质量检查报告（包含统计指标和改进建议）
- 退出码：0（成功）

【作者】
Claude Code Hook System

【版本】
1.0.0
"""
import sys
import json
from pathlib import Path
from datetime import datetime


def read_file_content(file_path: str) -> str:
    """
    读取文件内容

    Args:
        file_path: 文件路径

    Returns:
        str: 文件内容字符串

    Raises:
        Exception: 文件读取失败时抛出异常
    """
    return Path(file_path).read_text(encoding='utf-8')


def count_characters(content: str) -> int:
    """
    统计字符数

    Args:
        content: 文章内容

    Returns:
        int: 字符总数
    """
    return len(content)


def count_words(content: str) -> int:
    """
    统计词数（以空白字符分隔的片段数）

    Args:
        content: 文章内容

    Returns:
        int: 词数
    """
    return len(content.split())


def has_main_title(content: str) -> bool:
    """
    检查文章是否包含一级标题

    Args:
        content: 文章内容

    Returns:
        bool: 如果包含一级标题（# 开头）返回 True，否则返回 False
    """
    return content.strip().startswith('#')


def count_paragraphs(content: str) -> int:
    """
    统计段落数

    Args:
        content: 文章内容

    Returns:
        int: 段落数量（以双换行符分隔的非空段落）
    """
    paragraphs = [p for p in content.split('\n\n') if p.strip()]
    return len(paragraphs)


def generate_suggestions(char_count: int, has_title: bool, paragraph_count: int) -> list:
    """
    根据检查指标生成改进建议

    Args:
        char_count: 字符数
        has_title: 是否有一级标题
        paragraph_count: 段落数

    Returns:
        list: 建议列表，每个元素是一条建议字符串
    """
    suggestions = []

    if char_count < 500:
        suggestions.append("- 建议增加内容，至少 500 字")

    if not has_title:
        suggestions.append("- 建议添加一级标题（# 标题）")

    if paragraph_count < 3:
        suggestions.append("- 建议增加段落，改善可读性")

    return suggestions


def check_article_quality(file_path: str) -> str:
    """
    执行文章质量检查并生成报告

    Args:
        file_path: Markdown 文件路径

    Returns:
        str: 格式化的质量检查报告
    """
    # 读取文件内容
    try:
        content = read_file_content(file_path)
    except Exception as e:
        return f"无法读取文件：{e}"

    # 统计各项指标
    char_count = count_characters(content)
    word_count = count_words(content)
    has_title_flag = has_main_title(content)
    paragraph_count = count_paragraphs(content)

    # 生成建议列表
    suggestions = generate_suggestions(char_count, has_title_flag, paragraph_count)

    # 构建报告
    report = []
    report.append("\n" + "=" * 50)
    report.append("文章质量检查报告")
    report.append("=" * 50)

    # 统计指标部分
    title_status = "V" if char_count > 500 else "! 偏短"
    report.append(f"\n字符数：{char_count} {title_status}")

    report.append(f"词数：{word_count}")

    title_flag_str = "V 有" if has_title_flag else "X 缺少一级标题"
    report.append(f"标题：{title_flag_str}")

    paragraph_status = "V" if paragraph_count > 3 else "! 偏少"
    report.append(f"段落数：{paragraph_count} {paragraph_status}")

    # 建议部分
    if suggestions:
        report.append("\n改进建议:")
        report.extend(suggestions)
    else:
        report.append("\nV 文章质量良好！")

    report.append("=" * 50 + "\n")

    return '\n'.join(report)


def main():
    """
    主函数：处理 Markdown 文件写入后的质量检查逻辑

    执行流程：
    1. 从 stdin 读取并解析 JSON 输入
    2. 检查是否为 Write 工具和.md 文件
    3. 执行文章质量检查
    4. 在 stderr 输出检查报告
    5. 记录到日志文件
    """
    # 配置项：日志文件路径
    LOG_FILE = r"D:\Claude\PullRequest\post_article_quality.log"

    # 步骤 1: Hook 启动
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] [start] Hook 启动\n")

    # 步骤 2: 解析输入数据
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # JSON 解析失败，记录日志后退出
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] [parse_error] JSON 解析失败\n")
        return

    # 步骤 3: 记录输入解析成功
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tool_name = input_data.get('tool_name', 'Unknown')
        tool_input = input_data.get('tool_input', {})
        f.write(f"[{timestamp}] [parsed] {tool_name}: {tool_input}\n")

    # 步骤 4: 提取关键字段
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    # 步骤 5: 只处理 Write 工具和.md 文件
    if tool_name != 'Write' or not file_path.endswith('.md'):
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] [not_markdown_file] {tool_name}: file_path={file_path}\n")
        return

    # 步骤 6: 执行质量检查并获取报告
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] [checking_quality] {tool_name}: file_path={file_path}\n")
    report = check_article_quality(file_path)

    # 步骤 7: 在终端显示报告（输出到 stderr）
    print(report, file=sys.stderr)

    # 步骤 8: 记录到日志文件
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] [quality_check_completed] {tool_name}: file_path={file_path}\n")


if __name__ == '__main__':
    main()
