#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PreToolUse Hook - Git 提交前检查系统

【功能概述】
本钩子在执行 git commit 命令前自动运行，提供以下检查功能：
1. 分支检查：禁止直接提交到受保护分支（main/master/production）
2. 敏感信息检查：检测可能泄露的 API Key、密码、Token 等敏感信息
3. 代码风格检查：对 Python 文件运行 ruff，对 JS/TS 文件运行 eslint

【Hook 类型】
PreToolUse - 在工具执行前运行，可拦截操作

【触发条件】
- 工具名称：Bash
- 命令包含：git commit
- 触发时机：Bash 工具执行前

【检查项目】
1. 分支检查：
   - 受保护分支：main, master, production
   - 违反时：拒绝提交，提示使用 Pull Request

2. 敏感信息检查（正则匹配）：
   - API Key: api_key=, apikey= 等
   - 密码：secret=, password=, passwd=, pwd= 等
   - Token: access_token=, auth_token= 等
   - OpenAI API Key: sk- 开头
   - GitHub Token: ghp_ 开头

3. 代码风格检查：
   - Python 文件：使用 ruff check
   - JavaScript/TypeScript 文件：使用 eslint --quiet

【CLI 调用示例】
# 模拟 git commit 命令（触发完整检查）
echo {"tool_name":"Bash","tool_input":{"command":"git commit -m 'test'"}} | python git-pre-commit-checker.py

# 模拟其他命令（不触发）
echo {"tool_name":"Bash","tool_input":{"command":"git status"}} | python git-pre-commit-checker.py

【输入格式】
JSON 格式，通过 stdin 传入：
{
    "tool_name": "Bash",
    "tool_input": {
        "command": "git commit -m 'test'"
    }
}

【输出格式】
- stdout: JSON 格式的决策（当检查未通过时要求确认）
- stderr: 格式化的检查报告
- 退出码：0（成功）

【配置说明】
受保护分支和敏感信息模式可在 CONFIG 字典中配置

【作者】
Claude Code Hook System

【版本】
1.0.0
"""
import sys
import json
import subprocess
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


# =============================================================================
# 配置区域
# =============================================================================
CONFIG = {
    # 受保护的分支列表，禁止直接提交
    'protected_branches': ['main', 'master', 'production'],

    # 敏感信息检测的正则表达式模式
    'secret_patterns': [
        # API Key 模式：匹配 api_key=, apikey= 等形式
        r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[\w-]{20,}',
        # 密码模式：匹配 secret=, password=, passwd=, pwd= 等形式
        r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\']?[\w-]{8,}',
        # Token 模式：匹配 access_token=, auth_token= 等形式
        r'(?i)(access[_-]?token|auth[_-]?token)\s*[=:]\s*["\']?[\w-]{20,}',
        # OpenAI API Key 模式：sk- 开头，后跟至少 20 位字母数字
        r'sk-[a-zA-Z0-9]{20,}',
        # GitHub Personal Access Token 模式：ghp_ 开头
        r'ghp_[a-zA-Z0-9]{36,}',
    ],
}


def run_command(cmd: str, timeout: int = 60) -> tuple:
    """
    执行 Shell 命令并返回结果

    Args:
        cmd: 要执行的命令字符串
        timeout: 超时时间（秒），默认 60 秒

    Returns:
        tuple: (returncode, stdout, stderr)
            - returncode: 返回码，0 表示成功，-1 表示超时或异常
            - stdout: 标准输出
            - stderr: 标准错误

    Note:
        命令超时或发生异常时返回 (-1, '', '错误信息')
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, '', 'Command timed out'
    except Exception as e:
        return -1, '', str(e)


def check_branch() -> tuple:
    """
    检查当前 Git 分支是否在受保护列表中

    Returns:
        tuple: (passed, message)
            - passed: bool，检查是否通过
            - message: str，检查信息

    检查逻辑：
        1. 获取当前分支名称
        2. 如果分支在保护列表中，拒绝提交
        3. 否则允许提交
    """
    # 获取当前分支名称
    code, stdout, _ = run_command('git rev-parse --abbrev-ref HEAD')
    if code != 0:
        # 无法获取分支名称
        return True, "无法获取当前分支"

    branch = stdout.strip()

    # 检查是否在保护列表中
    if branch in CONFIG['protected_branches']:
        return False, f"X 禁止直接提交到受保护分支：{branch}\n请使用 Pull Request"

    return True, f"当前分支：{branch}"


def check_secrets() -> tuple:
    """
    检查暂存区文件中是否包含敏感信息

    Returns:
        tuple: (passed, message)
            - passed: bool，检查是否通过
            - message: str，检查信息

    检查逻辑：
        1. 获取 git diff --cached 的输出（暂存区变更）
        2. 使用正则模式匹配敏感信息
        3. 发现可疑内容时返回警告
    """
    # 获取暂存区的变更内容
    code, stdout, _ = run_command('git diff --cached')
    if code != 0:
        return True, "无法获取 diff"

    findings = []
    # 逐个模式匹配
    for pattern in CONFIG['secret_patterns']:
        if re.search(pattern, stdout):
            # 只显示模式的前 40 个字符，避免输出过长
            findings.append(f"发现可疑模式：{pattern[:40]}...")

    if findings:
        return False, "X 发现可能的敏感信息:\n" + '\n'.join(findings)

    return True, "敏感信息检查通过"


def check_lint() -> tuple:
    """
    对暂存区的代码文件进行风格检查

    Returns:
        tuple: (passed, message)
            - passed: bool，检查是否通过
            - message: str，检查信息

    检查逻辑：
        1. 获取暂存区变更的文件列表
        2. Python 文件 (.py) 使用 ruff check
        3. JavaScript/TypeScript 文件 (.js, .ts, .jsx, .tsx) 使用 eslint
        4. 汇总检查结果
    """
    # 获取暂存区变更的文件列表（仅新增、复制、修改的文件）
    code, stdout, _ = run_command('git diff --cached --name-only --diff-filter=ACMR')
    if code != 0:
        return True, "无法获取变更文件列表"

    # 解析文件列表
    files = [f for f in stdout.strip().split('\n') if f]

    # 按文件类型分类
    py_files = [f for f in files if f.endswith('.py')]
    js_files = [f for f in files if f.endswith(('.js', '.ts', '.jsx', '.tsx'))]

    errors = []

    # Python 文件检查
    if py_files:
        code, stdout, stderr = run_command(f'ruff check {" ".join(py_files)}')
        if code != 0:
            errors.append(f"Python 代码问题:\n{stdout or stderr}")

    # JavaScript/TypeScript 文件检查
    if js_files:
        code, stdout, stderr = run_command(f'npx eslint {" ".join(js_files)} --quiet')
        if code != 0:
            errors.append(f"JS/TS 代码问题:\n{stdout or stderr}")

    if errors:
        return False, '\n'.join(errors)

    return True, "代码风格检查通过"


def run_checks_parallel(checks: list) -> tuple:
    """
    并行执行所有检查

    Args:
        checks: 检查列表，每项为 (检查名称，检查函数) 的元组

    Returns:
        tuple: (results, all_passed)
            - results: 检查结果列表 [(name, passed, message), ...]
            - all_passed: bool，是否所有检查都通过
    """
    results = []
    all_passed = True

    # 使用线程池并行执行检查（最多 3 个线程）
    with ThreadPoolExecutor(max_workers=3) as executor:
        # 提交所有检查任务
        future_to_check = {executor.submit(check[1]): check[0] for check in checks}

        # 收集结果
        for future in as_completed(future_to_check):
            check_name = future_to_check[future]
            try:
                passed, message = future.result()
                results.append((check_name, passed, message))
                if not passed:
                    all_passed = False
            except Exception as e:
                # 检查执行异常
                results.append((check_name, False, f"检查异常：{str(e)}"))
                all_passed = False

    return results, all_passed


def print_report(results: list, all_passed: bool) -> None:
    """
    打印检查报告到 stderr

    Args:
        results: 检查结果列表 [(name, passed, message), ...]
        all_passed: 是否所有检查都通过
    """
    print("\n" + "=" * 60, file=sys.stderr)
    print("Git 提交前检查报告", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    for name, passed, message in results:
        status = "V PASS" if passed else "X FAIL"
        print(f"\n{status} {name}", file=sys.stderr)
        print(f"   {message}", file=sys.stderr)

    print("\n" + "=" * 60, file=sys.stderr)


def write_log(log_path: str) -> None:
    """
    写入 Hook 调用日志

    Args:
        log_path: 日志文件路径
    """
    with open(log_path, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] Hook 被调用 - Write 操作：\n")


def main():
    """
    主函数：处理 Git 提交前的检查逻辑

    执行流程：
    1. 从 stdin 读取并解析 JSON 输入
    2. 检查是否为 Bash 工具和 git commit 命令
    3. 并行执行所有检查（分支、敏感信息、代码风格）
    4. 输出检查报告
    5. 根据检查结果决定是否拦截提交
    6. 记录到日志文件
    """
    # 配置项：日志文件路径
    LOG_FILE = r"D:\Claude\PullRequest\it-_pre_commit_checker.log"

    # 步骤 1: 解析输入数据
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # JSON 解析失败，静默退出
        return

    # 步骤 2: 提取字段
    tool_name = input_data.get('tool_name', '')
    command = input_data.get('tool_input', {}).get('command', '')

    # 步骤 3: 只处理 git commit 命令
    if tool_name != 'Bash' or 'git commit' not in command:
        return

    # 步骤 4: 定义所有检查
    checks = [
        ('分支检查', check_branch),
        ('敏感信息', check_secrets),
        ('代码风格', check_lint),
    ]

    # 步骤 5: 并行执行检查
    results, all_passed = run_checks_parallel(checks)

    # 步骤 6: 输出检查报告
    print_report(results, all_passed)

    # 步骤 7: 根据检查结果输出决策
    if not all_passed:
        # 检查未通过，要求用户确认
        decision = {
            "decision": "ask",
            "message": "检查未通过，是否仍要继续提交？"
        }
        print(json.dumps(decision, ensure_ascii=False))
    else:
        # 所有检查通过
        print("所有检查通过，允许提交", file=sys.stderr)

    # 步骤 8: 记录到日志文件
    write_log(LOG_FILE)


if __name__ == '__main__':
    main()
