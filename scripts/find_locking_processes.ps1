param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$resolvedPath = [System.IO.Path]::GetFullPath($Path)

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class RestartManagerNative
{
    public const int CCH_RM_SESSION_KEY = 32;
    public const int ERROR_MORE_DATA = 234;

    [StructLayout(LayoutKind.Sequential)]
    public struct RM_UNIQUE_PROCESS
    {
        public int dwProcessId;
        public System.Runtime.InteropServices.ComTypes.FILETIME ProcessStartTime;
    }

    public enum RM_APP_TYPE
    {
        RmUnknownApp = 0,
        RmMainWindow = 1,
        RmOtherWindow = 2,
        RmService = 3,
        RmExplorer = 4,
        RmConsole = 5,
        RmCritical = 1000
    }

    [Flags]
    public enum RM_REBOOT_REASON
    {
        None = 0,
        PermissionDenied = 1,
        SessionMismatch = 2,
        CriticalProcess = 4,
        CriticalService = 8,
        DetectedSelf = 16
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct RM_PROCESS_INFO
    {
        public RM_UNIQUE_PROCESS Process;

        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 256)]
        public string strAppName;

        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)]
        public string strServiceShortName;

        public RM_APP_TYPE ApplicationType;
        public uint AppStatus;
        public uint TSSessionId;

        [MarshalAs(UnmanagedType.Bool)]
        public bool bRestartable;
    }

    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    public static extern int RmStartSession(out uint pSessionHandle, int dwSessionFlags, string strSessionKey);

    [DllImport("rstrtmgr.dll")]
    public static extern int RmEndSession(uint pSessionHandle);

    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    public static extern int RmRegisterResources(
        uint pSessionHandle,
        UInt32 nFiles,
        string[] rgsFilenames,
        UInt32 nApplications,
        RM_UNIQUE_PROCESS[] rgApplications,
        UInt32 nServices,
        string[] rgsServiceNames);

    [DllImport("rstrtmgr.dll")]
    public static extern int RmGetList(
        uint dwSessionHandle,
        out uint pnProcInfoNeeded,
        ref uint pnProcInfo,
        [In, Out] RM_PROCESS_INFO[] rgAffectedApps,
        ref uint lpdwRebootReasons);
}
"@

function Get-LockingProcesses {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ResourcePath
    )

    $sessionHandle = 0
    $sessionKey = [Guid]::NewGuid().ToString("N").Substring(0, [RestartManagerNative]::CCH_RM_SESSION_KEY)
    $startResult = [RestartManagerNative]::RmStartSession([ref]$sessionHandle, 0, $sessionKey)
    if ($startResult -ne 0) {
        throw "RmStartSession failed with code $startResult."
    }

    try {
        $registerResult = [RestartManagerNative]::RmRegisterResources($sessionHandle, 1, @($ResourcePath), 0, $null, 0, $null)
        if ($registerResult -ne 0) {
            throw "RmRegisterResources failed with code $registerResult."
        }

        $needed = 0
        $count = 0
        $rebootReasons = [uint32]0
        $listResult = [RestartManagerNative]::RmGetList($sessionHandle, [ref]$needed, [ref]$count, $null, [ref]$rebootReasons)

        if ($listResult -eq 0) {
            return @()
        }

        if ($listResult -ne [RestartManagerNative]::ERROR_MORE_DATA) {
            throw "RmGetList failed with code $listResult."
        }

        $count = $needed
        $processInfo = New-Object RestartManagerNative+RM_PROCESS_INFO[] $count
        $listResult = [RestartManagerNative]::RmGetList($sessionHandle, [ref]$needed, [ref]$count, $processInfo, [ref]$rebootReasons)
        if ($listResult -ne 0) {
            throw "RmGetList failed with code $listResult."
        }

        return $processInfo[0..($count - 1)]
    }
    finally {
        [void][RestartManagerNative]::RmEndSession($sessionHandle)
    }
}

function Get-FallbackCandidateProcesses {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ResourcePath
    )

    $escapedPath = [Regex]::Escape($ResourcePath)
    $escapedRoot = [Regex]::Escape((Split-Path -Parent $ResourcePath))
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            ($_.ExecutablePath -and $_.ExecutablePath -match $escapedRoot) -or
            ($_.CommandLine -and $_.CommandLine -match $escapedPath)
        } |
        Select-Object ProcessId, Name, ExecutablePath, CommandLine
}

try {
    if (-not (Test-Path -LiteralPath $resolvedPath)) {
        Write-Output "[WARN] Path not found: $resolvedPath"
        exit 0
    }

    Write-Output "[INFO] Checking for processes locking: $resolvedPath"
    $locking = @(Get-LockingProcesses -ResourcePath $resolvedPath)

    if ($locking.Count -eq 0) {
        Write-Output "[INFO] Restart Manager did not report any locking processes."
        exit 0
    }

    foreach ($entry in $locking) {
        $pid = $entry.Process.dwProcessId
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $pid" -ErrorAction SilentlyContinue
        $name = if ($process.Name) { $process.Name } elseif ($entry.strAppName) { $entry.strAppName } else { "unknown" }
        $exe = if ($process.ExecutablePath) { $process.ExecutablePath } else { "n/a" }
        $cmd = if ($process.CommandLine) { $process.CommandLine } else { "n/a" }
        Write-Output ("[LOCK] pid={0} name={1}" -f $pid, $name)
        Write-Output ("        exe={0}" -f $exe)
        Write-Output ("        cmd={0}" -f $cmd)
    }
}
catch {
    Write-Output "[WARN] Lock inspection failed: $($_.Exception.Message)"
    Write-Output "[INFO] Falling back to a process scan for matching paths..."
    $candidates = @(Get-FallbackCandidateProcesses -ResourcePath $resolvedPath)
    if ($candidates.Count -eq 0) {
        Write-Output "[INFO] No candidate processes matched the path during fallback scan."
        exit 1
    }

    foreach ($candidate in $candidates) {
        $exe = if ($candidate.ExecutablePath) { $candidate.ExecutablePath } else { "n/a" }
        $cmd = if ($candidate.CommandLine) { $candidate.CommandLine } else { "n/a" }
        Write-Output ("[CANDIDATE] pid={0} name={1}" -f $candidate.ProcessId, $candidate.Name)
        Write-Output ("            exe={0}" -f $exe)
        Write-Output ("            cmd={0}" -f $cmd)
    }
    exit 1
}
