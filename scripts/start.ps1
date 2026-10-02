param([switch]$Production)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw '请先运行 scripts/setup.ps1 创建项目环境。' }
$runtimePath = Join-Path $projectRoot '.runtime'
New-Item -ItemType Directory -Path $runtimePath -Force | Out-Null
foreach ($port in @(8010,3000)) {
  if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "端口 $port 已被占用；请先核实已有服务，不自动终止其他程序。" }
}
$backendProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8010') -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimePath 'backend.out.log') -RedirectStandardError (Join-Path $runtimePath 'backend.err.log')
$nodeCommand = (Get-Command node.exe).Source
$nextPath = Join-Path $projectRoot 'frontend/node_modules/next/dist/bin/next'
$mode = if ($Production) { 'start' } else { 'dev' }
$frontendProcess = Start-Process -FilePath $nodeCommand -ArgumentList @($nextPath,$mode,'--hostname','127.0.0.1','--port','3000') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimePath 'frontend.out.log') -RedirectStandardError (Join-Path $runtimePath 'frontend.err.log')
@{ backend=$backendProcess.Id; frontend=$frontendProcess.Id; backendExecutable=$pythonPath; frontendExecutable=$nodeCommand; createdAt=(Get-Date).ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimePath 'processes.json') -Encoding utf8
Write-Output '沪讯正在启动：http://127.0.0.1:3000'
Write-Output 'API 文档：http://127.0.0.1:8010/docs'
