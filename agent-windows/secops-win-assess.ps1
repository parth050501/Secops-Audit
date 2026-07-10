# secops-win-assess.ps1
# Code Core Systems — Windows compliance posture collector.
# Runs READ-ONLY queries of Windows security settings and emits a JSON document
# that the platform ingests and assesses against compliance controls.
#
# This script COLLECTS settings only — it makes no changes and judges nothing.
# All compliance logic lives in the platform (APE), so checks can change without
# updating this script.
#
# Usage (run as Administrator for full coverage):
#   powershell -ExecutionPolicy Bypass -File secops-win-assess.ps1 > assessment.json
#
# On-prem, the agent runs this and ships the JSON to the collection engine.

$ErrorActionPreference = "SilentlyContinue"

function Get-SecPol {
    $tmp = "$env:TEMP\secpol.cfg"
    secedit /export /cfg $tmp /quiet | Out-Null
    $cfg = @{}
    Get-Content $tmp | ForEach-Object {
        if ($_ -match "^\s*([^=]+?)\s*=\s*(.+?)\s*$") { $cfg[$matches[1]] = $matches[2] }
    }
    Remove-Item $tmp -ErrorAction SilentlyContinue
    return $cfg
}

$sp = Get-SecPol

# Password policy
$pw = @{
    min_length    = [int]$sp["MinimumPasswordLength"]
    complexity    = ([int]$sp["PasswordComplexity"] -eq 1)
    max_age_days  = [int]$sp["MaximumPasswordAge"]
    min_age_days  = [int]$sp["MinimumPasswordAge"]
    history_count = [int]$sp["PasswordHistorySize"]
}

# Lockout policy
$lock = @{
    threshold    = [int]$sp["LockoutBadCount"]
    duration_min = [int]$sp["LockoutDuration"]
    window_min   = [int]$sp["ResetLockoutCount"]
}

# Audit policy (auditpol)
function Get-Audit($sub) {
    $line = (auditpol /get /subcategory:"$sub") 2>$null | Select-String $sub
    if ($line -match "Success and Failure") { return "Success and Failure" }
    elseif ($line -match "Success") { return "Success" }
    elseif ($line -match "Failure") { return "Failure" }
    else { return "No Auditing" }
}
$audit = @{
    logon         = Get-Audit "Logon"
    account_logon = Get-Audit "Credential Validation"
    policy_change = Get-Audit "Audit Policy Change"
    privilege_use = Get-Audit "Sensitive Privilege Use"
}

# Security options
$smbv1 = $false
$f = Get-WindowsOptionalFeature -Online -FeatureName SMB1Protocol -ErrorAction SilentlyContinue
if ($f -and $f.State -eq "Enabled") { $smbv1 = $true }

$nla = (Get-ItemProperty "HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" -Name UserAuthentication -ErrorAction SilentlyContinue).UserAuthentication -eq 1
$guest = (Get-LocalUser -Name "Guest" -ErrorAction SilentlyContinue).Enabled -eq $true
$lm = (Get-ItemProperty "HKLM:\System\CurrentControlSet\Control\Lsa" -Name NoLMHash -ErrorAction SilentlyContinue).NoLMHash -ne 1

$secopts = @{
    smbv1_enabled         = $smbv1
    rdp_nla_required      = [bool]$nla
    guest_account_enabled = [bool]$guest
    lm_hash_stored        = [bool]$lm
}

# Services
$svc = @{
    telnet_running = ((Get-Service -Name "TlntSvr" -ErrorAction SilentlyContinue).Status -eq "Running")
    ftp_running    = ((Get-Service -Name "FTPSVC" -ErrorAction SilentlyContinue).Status -eq "Running")
}

# Firewall profiles
$fwp = Get-NetFirewallProfile -ErrorAction SilentlyContinue
$fw = @{
    domain_profile  = (($fwp | Where-Object Name -eq "Domain").Enabled -eq $true)
    private_profile = (($fwp | Where-Object Name -eq "Private").Enabled -eq $true)
    public_profile  = (($fwp | Where-Object Name -eq "Public").Enabled -eq $true)
}

$result = @{
    hostname        = $env:COMPUTERNAME
    os              = (Get-CimInstance Win32_OperatingSystem).Caption
    password_policy = $pw
    lockout_policy  = $lock
    audit_policy    = $audit
    security_options= $secopts
    services        = $svc
    firewall        = $fw
}

$result | ConvertTo-Json -Depth 5
