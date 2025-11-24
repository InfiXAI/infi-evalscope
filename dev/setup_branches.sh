#!/bin/bash
# 初始化分支结构脚本
# 用于设置 main、internal-main、dev 分支结构

set -e

echo "=== 初始化分支结构 ==="

# 1. 确保 upstream 远程仓库已配置
if ! git remote | grep -q upstream; then
    echo "添加 upstream 远程仓库..."
    git remote add upstream https://github.com/modelscope/evalscope.git
    echo "✓ upstream 远程仓库已添加"
else
    echo "✓ upstream 远程仓库已存在"
fi

# 2. 更新 upstream 信息
echo "获取 upstream 最新信息..."
git fetch upstream

# 3. 确保 main 分支与 upstream/main 同步
echo "同步 main 分支..."
git checkout main
git pull upstream main
git push origin main
echo "✓ main 分支已与 upstream/main 同步"

# 4. 创建 internal-main 分支（如果不存在）
if git show-ref --verify --quiet refs/heads/internal-main; then
    echo "✓ internal-main 分支已存在"
    git checkout internal-main
    git pull origin internal-main
else
    echo "创建 internal-main 分支..."
    git checkout -b internal-main
    git push -u origin internal-main
    echo "✓ internal-main 分支已创建并推送"
fi

# 5. 确保 dev 分支存在
if git show-ref --verify --quiet refs/heads/dev; then
    echo "✓ dev 分支已存在"
else
    echo "创建 dev 分支..."
    git checkout -b dev
    git push -u origin dev
    echo "✓ dev 分支已创建并推送"
fi

echo ""
echo "=== 分支结构初始化完成 ==="
echo "当前分支结构："
echo "  - main: 与上游官方仓库同步"
echo "  - internal-main: 内部稳定版本分支"
echo "  - dev: 开发分支"
echo ""
echo "使用 'git checkout dev' 切换到开发分支开始工作"

