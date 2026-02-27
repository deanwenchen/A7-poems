# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains classical Chinese poetry collections. Each poet's works are stored in a separate UTF-8 encoded text file named `{诗人}诗选.txt`.

## Repository Structure

- **李白诗选.txt** - Li Bai's poems
- **杜甫诗选.txt**, **杜甫诗选 2.txt** - Du Fu's poems
- **李清照诗选.txt** - Li Qingzhao's poems
- **陶渊明诗选.txt** - Tao Yuanming's poems

## Poetry File Format

Poems are formatted in classical Chinese style:
```
《诗题》
诗句第一行
诗句第二行
...

《下一首诗题》
...
```

## Git Workflow

- Main branch: `main`
- Remote: `origin` at `https://github.com/deanwenchen/A7-poems.git`
- Commit messages are in Chinese (e.g., "添加李白诗选文件")

## Claude Configuration

- **Hook**: `.claude/hooks/post-write-hello.py` - Displays a confirmation message after each `Write` tool execution
- **Permissions**: `.claude/settings.local.json` allows `dir` Bash commands
