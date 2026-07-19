[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("start", "stop", "logs", "backup")]
    [string]$Action,

    [Parameter(Position = 1)]
    [ValidateSet("backend", "hermes")]
    [string]$Service
)

$ErrorActionPreference = "Stop"
$DesktopDir = $PSScriptRoot
$ComposeFile = Join-Path $DesktopDir "compose.yaml"
$EnvFile = Join-Path $DesktopDir ".env"
Set-Location -LiteralPath $DesktopDir
$ComposeManagedVariables = @(
    "COMPOSE_PROJECT_NAME", "APP_PORT", "HERMES_PORT", "OPENAI_API_KEY",
    "OPENAI_BASE_URL", "OPENAI_MODEL",
    "HERMES_API_SERVER_KEY", "BACKUP_IMAGE", "PIP_INDEX_URL",
    "REQUIREMENTS_FILE", "HERMES_REASONING_EFFORT", "HERMES_MAX_TURNS",
    "HERMES_MAX_CONCURRENT_RUNS", "HERMES_TERMINAL_TIMEOUT",
    "HERMES_REQUEST_TIMEOUT", "HERMES_WEB_BACKEND", "HERMES_WEB_SEARCH_BACKEND",
    "FIRECRAWL_API_KEY", "TAVILY_API_KEY", "EXA_API_KEY", "PARALLEL_API_KEY"
)

function Invoke-Compose {
    $saved = @{}
    foreach ($name in $ComposeManagedVariables) {
        $existing = [Environment]::GetEnvironmentVariable($name, "Process")
        if ($null -ne $existing) {
            $saved[$name] = $existing
            Remove-Item -Path "Env:$name" -ErrorAction SilentlyContinue
        }
    }
    try {
        & docker compose --env-file $EnvFile --project-directory $DesktopDir -f $ComposeFile @args
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        foreach ($name in $saved.Keys) {
            [Environment]::SetEnvironmentVariable($name, $saved[$name], "Process")
        }
    }
}

function Assert-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker was not found. Install and start Docker Desktop first."
    }
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker is installed but the daemon is not running."
    }
    & docker compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "The Docker Compose plugin is required (docker compose)."
    }
}

function Get-EnvValue([string]$Name) {
    if (-not (Test-Path -LiteralPath $EnvFile)) {
        return ""
    }
    $result = ""
    foreach ($line in [IO.File]::ReadAllLines($EnvFile)) {
        if ($line.StartsWith("$Name=")) {
            $result = $line.Substring($Name.Length + 1).Trim()
            if (($result.StartsWith('"') -and $result.EndsWith('"')) -or
                ($result.StartsWith("'") -and $result.EndsWith("'"))) {
                $result = $result.Substring(1, $result.Length - 2)
            }
        }
    }
    return $result
}

function New-HermesKey {
    $bytes = New-Object byte[] 32
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }
    $hex = -join ($bytes | ForEach-Object { $_.ToString("x2") })
    return "desktop-$hex"
}

function Set-EnvValue([string]$Name, [string]$Value) {
    $content = [IO.File]::ReadAllText($EnvFile)
    $pattern = "(?m)^" + [Regex]::Escape($Name) + "=.*(?:\r?\n|$)"
    $line = "$Name=$Value" + [Environment]::NewLine
    if ([Regex]::IsMatch($content, $pattern)) {
        $content = [Regex]::Replace($content, $pattern, $line)
    }
    else {
        if ($content.Length -gt 0 -and -not $content.EndsWith("`n")) {
            $content += [Environment]::NewLine
        }
        $content += $line
    }
    $utf8NoBom = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($EnvFile, $content, $utf8NoBom)
}

function Initialize-Env {
    $script:EnvCreated = $false
    if (-not (Test-Path -LiteralPath $EnvFile)) {
        Copy-Item -LiteralPath (Join-Path $DesktopDir ".env.example") -Destination $EnvFile
        $script:EnvCreated = $true
    }
    $hermesKey = Get-EnvValue "HERMES_API_SERVER_KEY"
    if ($hermesKey -in @("", "__GENERATE_ON_FIRST_START__", "change-me", "change-this-to-a-random-long-string")) {
        Set-EnvValue "HERMES_API_SERVER_KEY" (New-HermesKey)
    }
}

function Test-TemplateValue([string]$Value) {
    $normalized = $Value.ToLowerInvariant()
    return [string]::IsNullOrWhiteSpace($Value) -or
        $normalized.Contains("replace-with") -or
        $normalized.Contains("replace_me") -or
        $normalized.Contains("your-key") -or
        $normalized.Contains("your_key") -or
        $normalized.Contains("change-me") -or
        $normalized.Contains("changeme") -or
        $normalized.Contains("placeholder") -or
        $normalized.Contains("example.com") -or
        $normalized.StartsWith("__")
}

function Assert-Port([string]$Name, [string]$Value) {
    $number = 0
    if (-not ([int]::TryParse($Value, [ref]$number)) -or $number -lt 1 -or $number -gt 65535) {
        throw "$Name must be a number between 1 and 65535."
    }
}

function Assert-Env {
    $modelName = Get-EnvValue "OPENAI_MODEL"
    $openAiKey = Get-EnvValue "OPENAI_API_KEY"
    $modelUrl = Get-EnvValue "OPENAI_BASE_URL"
    $hermesKey = Get-EnvValue "HERMES_API_SERVER_KEY"

    if ((Test-TemplateValue $openAiKey) -or $openAiKey.Length -lt 8) { throw "Set OPENAI_API_KEY in deploy/desktop/.env." }
    if (Test-TemplateValue $modelUrl) { throw "Set OPENAI_BASE_URL in deploy/desktop/.env." }
    if (Test-TemplateValue $modelName) {
        throw "Set OPENAI_MODEL in deploy/desktop/.env."
    }
    if ((Test-TemplateValue $hermesKey) -or $hermesKey.Length -lt 16) {
        throw "HERMES_API_SERVER_KEY must contain at least 16 non-template characters."
    }
    if ($hermesKey -eq $openAiKey) {
        throw "HERMES_API_SERVER_KEY must not reuse a model provider key."
    }

    $appPort = Get-EnvValue "APP_PORT"
    $hermesPort = Get-EnvValue "HERMES_PORT"
    if ([string]::IsNullOrEmpty($appPort)) { $appPort = "8501" }
    if ([string]::IsNullOrEmpty($hermesPort)) { $hermesPort = "8642" }
    Assert-Port "APP_PORT" $appPort
    Assert-Port "HERMES_PORT" $hermesPort
    if ($appPort -eq $hermesPort) {
        throw "APP_PORT and HERMES_PORT must be different."
    }
}

function Initialize-Runtime {
    $directories = @(
        "runtime/data/uploads",
        "runtime/data/tasks",
        "runtime/data/workspaces",
        "runtime/data/vision-cache",
        "runtime/data/knowledge",
        "runtime/logs",
        "runtime/outputs",
        "runtime/state",
        "runtime/hermes",
        "runtime/hermes/workspace",
        "backups"
    )
    foreach ($directory in $directories) {
        New-Item -ItemType Directory -Force -Path (Join-Path $DesktopDir $directory) | Out-Null
    }
    if (-not $env:HOST_UID) { $env:HOST_UID = "1000" }
    if (-not $env:HOST_GID) { $env:HOST_GID = "1000" }
}

function Start-Desktop {
    Initialize-Env
    if ($script:EnvCreated) {
        Write-Host "Created deploy/desktop/.env with a random Hermes API key."
        Write-Host "Set OPENAI_API_KEY, OPENAI_BASE_URL and OPENAI_MODEL, then run start.bat again."
        Start-Process notepad.exe -ArgumentList $EnvFile
        return
    }
    Assert-Env
    Initialize-Runtime

    $timeout = if ($env:STARTUP_TIMEOUT) { $env:STARTUP_TIMEOUT } else { "900" }
    Invoke-Compose up --detach --build --wait --wait-timeout $timeout

    $appPort = Get-EnvValue "APP_PORT"
    if ([string]::IsNullOrEmpty($appPort)) { $appPort = "8501" }
    $url = "http://127.0.0.1:$appPort"
    Write-Host "Desktop services are healthy. Open: $url"
    Start-Process $url
}

function Stop-Desktop {
    Invoke-Compose down --remove-orphans
    Write-Host "Desktop services stopped. Runtime data was preserved."
}

function Show-Logs {
    if ($Service) {
        Invoke-Compose logs --follow --tail 200 $Service
    }
    else {
        Invoke-Compose logs --follow --tail 200
    }
}

function Backup-Desktop {
    Initialize-Env
    Assert-Env
    Initialize-Runtime

    $running = @(Invoke-Compose ps --services --status running)
    $wasBackend = $running -contains "backend"
    $wasHermes = $running -contains "hermes"
    $stopped = $false

    try {
        if ($wasBackend -or $wasHermes) {
            $stopped = $true
            if ($wasBackend) {
                Invoke-Compose stop backend
            }
            if ($wasHermes) {
                Invoke-Compose stop hermes
            }
        }

        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupFile = "eia-desktop-$stamp.tgz"
        $env:BACKUP_FILE = $backupFile
        Invoke-Compose --profile tools run --rm --no-deps backup

        $backupPath = Join-Path (Join-Path $DesktopDir "backups") $backupFile
        if (-not (Test-Path -LiteralPath $backupPath) -or (Get-Item $backupPath).Length -eq 0) {
            throw "Backup archive was not created."
        }
        Write-Host "Backup created: $backupPath"
        Write-Host "Model keys and Hermes API keys are excluded; back up deploy/desktop/.env separately if required."
    }
    finally {
        if ($stopped) {
            $timeout = if ($env:STARTUP_TIMEOUT) { $env:STARTUP_TIMEOUT } else { "900" }
            if ($wasHermes -and $wasBackend) {
                Invoke-Compose start --wait --wait-timeout $timeout hermes backend
            }
            elseif ($wasHermes) {
                Invoke-Compose start --wait --wait-timeout $timeout hermes
            }
            elseif ($wasBackend) {
                Invoke-Compose start --wait --wait-timeout $timeout backend
            }
        }
    }
}

Assert-Docker
switch ($Action) {
    "start" { Start-Desktop }
    "stop" { Stop-Desktop }
    "logs" { Show-Logs }
    "backup" { Backup-Desktop }
}
