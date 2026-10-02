$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$recordPath = Join-Path $projectRoot '.runtime/processes.json'
if (-not (Test-Path -LiteralPath $recordPath)) { Write-Output '没有由启动脚本记录的进程。'; exit }
$record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
$allProcesses = @(Get-CimInstance Win32_Process)
function Stop-ProjectTree([int]$processNumber) {
  foreach ($child in $allProcesses | Where-Object { $_.ParentProcessId -eq $processNumber }) {
    Stop-ProjectTree $child.ProcessId
  }
  Stop-Process -Id $processNumber -ErrorAction SilentlyContinue
}
foreach ($name in @('backend','frontend')) {
  $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($record.$name)" -ErrorAction SilentlyContinue
  if ($taskProcess -and [Math]::Abs(($taskProcess.CreationDate - [datetime]$record.createdAt).TotalSeconds) -gt 60) { continue }
  if ($taskProcess -and $taskProcess.CommandLine -like "*$projectRoot*") {
    Stop-ProjectTree $taskProcess.ProcessId
  } elseif ($taskProcess -and $name -eq 'backend' -and $taskProcess.ExecutablePath -eq $record.backendExecutable) {
    Stop-ProjectTree $taskProcess.ProcessId
  }
}
Write-Output '已停止本项目记录且身份匹配的进程。'
