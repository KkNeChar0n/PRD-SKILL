#!/bin/bash
# PRD-SKILL Uninstaller
# 卸载 PRD-SKILL 套件下的 skill；默认从 Claude Code 卸载，可用 SKILLS_ROOT 指定其他目录。

set -e

SKILLS_ROOT="${SKILLS_ROOT:-$HOME/.claude/skills}"

SKILLS=(
  "prd"
  "prd-feishu-init"
  "prd-feishu"
  "prd-feishu-edit"
  "prd-feishu-batch"
  "uat-checklist"
  "gray-report"
  "regression-report"
)

echo "Uninstalling PRD-SKILL bundle (${#SKILLS[@]} skills)..."

for s in "${SKILLS[@]}"; do
  D="$SKILLS_ROOT/$s"
  if [ -d "$D" ]; then
    rm -rf "$D"
    echo "  ✓ Removed: $D"
  else
    echo "  - Skipped (not installed): $D"
  fi
done

echo ""
echo "Done!"
echo ""
echo "提示：本脚本不会删除以下凭证文件（含敏感信息）："
echo "  ~/.prd-feishu/config.json     # 飞书自建应用凭证"
echo ""
echo "如需清除，请手动执行：rm -f ~/.prd-feishu/config.json"
