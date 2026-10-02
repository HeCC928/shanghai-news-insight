$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { python -m venv (Join-Path $projectRoot '.venv'); if ($LASTEXITCODE) { throw 'Python 环境创建失败' } }
& $pythonPath -m pip install -r (Join-Path $projectRoot 'backend/requirements.lock')
if ($LASTEXITCODE) { throw '后端依赖安装失败' }
npm.cmd --prefix (Join-Path $projectRoot 'frontend') ci --no-audit --no-fund
if ($LASTEXITCODE) { throw '前端依赖安装失败' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '.env'))) { Copy-Item -LiteralPath (Join-Path $projectRoot '.env.example') -Destination (Join-Path $projectRoot '.env') }
Write-Output '环境已准备。可运行 scripts/start.ps1。'
