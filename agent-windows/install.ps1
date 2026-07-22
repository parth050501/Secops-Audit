# CodeCore Windows Agent installer (run as Administrator).
# Installs the agent and registers a daily scheduled task.
$ErrorActionPreference = "Stop"
Write-Host "Installing CodeCore Windows Agent..."

$InstallDir = "C:\Program Files\CodeCoreAgent"
$DataDir = "C:\ProgramData\CodeCore"
New-Item -ItemType Directory -Force -Path $InstallDir, $DataDir | Out-Null

Copy-Item -Recurse -Force .\codecore_agent $InstallDir\
Copy-Item -Force .\secops-win-assess.ps1 $InstallDir\

# Requires Python 3 + requests on the host
python -m pip install -r requirements.txt

if (-not (Test-Path "$DataDir\agent.conf")) {
    Copy-Item .\agent.conf.example "$DataDir\agent.conf"
    Write-Host "Created $DataDir\agent.conf - edit it with your collector URL + enroll secret."
}

# Daily scheduled task at 2 AM
$action = New-ScheduledTaskAction -Execute "python" -Argument "-m codecore_agent.agent --once" -WorkingDirectory $InstallDir
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -TaskName "CodeCoreAgent" -Action $action -Trigger $trigger -RunLevel Highest -Force

Write-Host "Installed. Edit $DataDir\agent.conf, then run once to test:"
Write-Host "  cd '$InstallDir'; python -m codecore_agent.agent --once"
