# suoha-serenity-skill installer (Windows PowerShell) — 本项目由 X 博主 梭哈.AI（@suoha_AI）设计和维护
# 用法： .\install.ps1 [-Target auto|claude|codex|agents|all]
param([ValidateSet("auto", "claude", "codex", "agents", "all")][string]$Target = "auto")
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$Name = "suoha-serenity-skill"
$Py = $null
foreach ($c in @("py -3", "python", "python3")) {
  $parts = $c.Split(" ")
  try {
    & $parts[0] @($parts[1..9] | Where-Object { $_ }) -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) { $Py = $parts; break }
  } catch {}
}
if (-not $Py) { Write-Host "❌ 需要 Python 3.10+（https://www.python.org/downloads/）"; exit 1 }
function Invoke-Py {
  param([string[]]$Args2)
  $out = & $Py[0] @($Py[1..9] | Where-Object { $_ }) @Args2 2>&1
  if ($LASTEXITCODE -ne 0) {
    $out | Select-Object -Last 20 | ForEach-Object { Write-Host $_ }
    Write-Host "❌ 安装失败：$($Args2 -join ' ')"
    Write-Host "   请把上面的输出贴到 https://github.com/suoha888/suoha-serenity-skill/issues"
    exit 1
  }
}

$H = if ($env:SUOHA_INSTALL_ROOT) { $env:SUOHA_INSTALL_ROOT } else { $HOME }
$bases = switch ($Target) {
  "claude" { @("$H\.claude\skills") }
  "codex"  { @("$H\.codex\skills") }
  "agents" { @("$H\.agents\skills") }
  "all"    { @("$H\.claude\skills", "$H\.codex\skills", "$H\.agents\skills") }
  default  {
    $f = @(); if (Test-Path "$H\.claude") { $f += "$H\.claude\skills" }; if (Test-Path "$H\.codex") { $f += "$H\.codex\skills" }
    if ($f.Count -eq 0) { $f = @("$H\.claude\skills") }; $f
  }
}
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
Invoke-Py @("scripts/validate_skill.py", ".", "--strict", "--any-folder")
foreach ($base in $bases) {
  New-Item -ItemType Directory -Force -Path $base | Out-Null
  $dest = Join-Path $base $Name
  if (Test-Path (Join-Path $dest "BUILD-MANIFEST.json")) {
    Invoke-Py @("scripts/build_runtime.py", "--source", ".", "--output", $dest, "--replace")
  } else {
    if (Test-Path $dest) { $bak = "$dest.bak-$(Get-Date -Format yyyyMMddHHmmss)"; Move-Item $dest $bak; Write-Host "ℹ️  旧目录已备份到 $bak" }
    Invoke-Py @("scripts/build_runtime.py", "--source", ".", "--output", $dest)
  }
  Invoke-Py @("scripts/verify_runtime.py", "--source", ".", "--runtime", $dest)
  Write-Host "✅ 已安装并校验：$dest"
}
Write-Host ""
Write-Host "下一步：在智能体里说「用 suoha-serenity-skill 研究 MU」，或在本目录运行："
Write-Host "  python suoha.py doctor ; python suoha.py research MU"
