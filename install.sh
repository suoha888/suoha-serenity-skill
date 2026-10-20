#!/usr/bin/env bash
# suoha-serenity-skill installer — 本项目由 X 博主 梭哈.AI（@suoha_AI）设计和维护
# 用法： ./install.sh            安装到所有检测到的智能体（Claude Code / Codex / 通用 .agents）
#        ./install.sh claude     只装 Claude Code（~/.claude/skills）
#        ./install.sh codex      只装 Codex（~/.codex/skills）
#        ./install.sh agents     只装通用目录（~/.agents/skills）
#        ./install.sh all        三处都装
set -euo pipefail
cd "$(dirname "$0")"
NAME="suoha-serenity-skill"
INSTALL_ROOT="${SUOHA_INSTALL_ROOT:-$HOME}"
export PYTHONUTF8=1
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then PY="$c"; break; fi
  done
fi
[ -n "$PY" ] || { echo "❌ 需要 Python 3.10+（https://www.python.org/downloads/）"; exit 1; }

target_dirs() {
  case "${1:-auto}" in
    claude) echo "$INSTALL_ROOT/.claude/skills" ;;
    codex)  echo "$INSTALL_ROOT/.codex/skills" ;;
    agents) echo "$INSTALL_ROOT/.agents/skills" ;;
    all)    printf '%s\n' "$INSTALL_ROOT/.claude/skills" "$INSTALL_ROOT/.codex/skills" "$INSTALL_ROOT/.agents/skills" ;;
    auto)
      found=0
      for d in "$INSTALL_ROOT/.claude" "$INSTALL_ROOT/.codex"; do
        if [ -d "$d" ]; then echo "$d/skills"; found=1; fi
      done
      [ "$found" = 1 ] || echo "$INSTALL_ROOT/.claude/skills" ;;
    *) echo "未知目标：$1（可选 claude|codex|agents|all）" >&2; exit 2 ;;
  esac
}

run() {  # quiet on success, show the tool's own output on failure
  local out
  if ! out=$("$PY" "$@" 2>&1); then
    echo "$out" | tail -20
    echo "❌ 安装失败：$PY $*"
    echo "   请把上面的输出贴到 https://github.com/suoha888/suoha-serenity-skill/issues"
    exit 1
  fi
}
run scripts/validate_skill.py . --strict --any-folder
while IFS= read -r base; do
  mkdir -p "$base"
  dest="$base/$NAME"
  if [ -f "$dest/BUILD-MANIFEST.json" ]; then
    run scripts/build_runtime.py --source . --output "$dest" --replace
  else
    if [ -e "$dest" ]; then
      bak="$dest.bak-$(date +%Y%m%d%H%M%S)"; mv "$dest" "$bak"; echo "ℹ️  旧目录已备份到 $bak"
    fi
    run scripts/build_runtime.py --source . --output "$dest"
  fi
  run scripts/verify_runtime.py --source . --runtime "$dest"
  echo "✅ 已安装并校验：$dest"
done < <(target_dirs "${1:-auto}")
echo
echo "下一步：在智能体里说「用 suoha-serenity-skill 研究 MU」，或在本目录运行："
echo "  $PY suoha.py doctor && $PY suoha.py research MU"
