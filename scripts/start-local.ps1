[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$DepsOnly,
    [switch]$NoBackend,
    [switch]$NoFrontend
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Read-DotEnv {
    param([string]$Path)

    $values = @{}
    if (-not (Test-Path $Path)) {
        return $values
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line -match "^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$") {
            $name = $Matches[1]
            $value = $Matches[2].Trim()
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            $values[$name] = $value
        }
    }

    return $values
}

$DotEnv = Read-DotEnv (Join-Path $RepoRoot ".env")

function Get-Setting {
    param(
        [string]$Name,
        [string]$Default = ""
    )

    $processValue = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ($processValue) {
        return $processValue
    }
    if ($DotEnv.ContainsKey($Name)) {
        return $DotEnv[$Name]
    }
    return $Default
}

function Get-AliasedSetting {
    param(
        [string[]]$Names,
        [string]$Default = ""
    )

    foreach ($name in $Names) {
        $value = Get-Setting $name
        if ($value) {
            return $value
        }
    }
    return $Default
}

function Set-AppEnv {
    param(
        [string]$Name,
        [string]$Value
    )

    if ($null -ne $Value) {
        [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
    }
}

function ConvertTo-Bool {
    param([string]$Value)
    return $Value -match "^(1|true|yes|on)$"
}

function Test-TcpPort {
    param(
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutMs = 1500
    )

    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $connect = $client.BeginConnect($HostName, $Port, $null, $null)
        $connected = $connect.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        if (-not $connected) {
            $client.Close()
            return $false
        }

        $client.EndConnect($connect)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

function Test-HttpEndpoint {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

function Test-BackendHealth {
    param([int]$Port)
    return Test-HttpEndpoint "http://127.0.0.1:$Port/health"
}

function Wait-BackendHealth {
    param(
        [int]$Port,
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-BackendHealth $Port) {
            return $true
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Get-DatabaseUrl {
    $configured = Get-Setting "DATABASE_URL"
    if ($configured) {
        return $configured
    }

    $db = Get-Setting "POSTGRES_DB" "mindmesh"
    $user = Get-Setting "POSTGRES_USER" "mindmesh_user"
    $password = Get-Setting "POSTGRES_PASSWORD" "mindmesh_password"
    $hostName = Get-Setting "POSTGRES_HOST" "localhost"
    $port = Get-Setting "POSTGRES_PORT" "5432"
    return "postgresql://${user}:${password}@${hostName}:${port}/${db}"
}

function Get-DatabaseTarget {
    param([string]$DatabaseUrl)

    try {
        $uri = [Uri]$DatabaseUrl
        $port = if ($uri.Port -gt 0) { $uri.Port } else { 5432 }
        return @{ HostName = $uri.Host; Port = $port }
    } catch {
        return @{
            HostName = Get-Setting "POSTGRES_HOST" "localhost"
            Port = [int](Get-Setting "POSTGRES_PORT" "5432")
        }
    }
}

function Get-ComposeDatabaseUrl {
    $db = Get-Setting "POSTGRES_DB" "mindmesh"
    $user = Get-Setting "POSTGRES_USER" "mindmesh_user"
    $password = Get-Setting "POSTGRES_PASSWORD" "mindmesh_password"
    $port = Get-Setting "POSTGRES_PORT" "5433"
    return "postgresql://${user}:${password}@localhost:${port}/${db}"
}

function Get-QdrantUrl {
    $configured = Get-Setting "QDRANT_URL"
    if ($configured) {
        return $configured.TrimEnd("/")
    }

    $port = Get-Setting "QDRANT_HTTP_PORT" "6333"
    return "http://localhost:${port}"
}

function Get-ComposeQdrantUrl {
    $port = Get-Setting "QDRANT_HTTP_PORT" "6335"
    return "http://localhost:${port}"
}

function Get-MinioEndpoint {
    $configured = Get-Setting "MINIO_ENDPOINT"
    if ($configured) {
        return $configured
    }

    $port = Get-Setting "MINIO_API_PORT" "9000"
    return "localhost:${port}"
}

function Get-MinioBaseUrl {
    param([string]$Endpoint)

    if ($Endpoint -match "^https?://") {
        return $Endpoint.TrimEnd("/")
    }

    $scheme = if (ConvertTo-Bool (Get-Setting "MINIO_SECURE" "false")) { "https" } else { "http" }
    return "${scheme}://${Endpoint}".TrimEnd("/")
}

function Start-ComposeServices {
    param([string[]]$Services)

    if (-not $Services -or $Services.Count -eq 0) {
        return
    }

    Write-Host "Starting missing dependencies with Docker Compose: $($Services -join ', ')"
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        & docker compose up -d @Services
        return
    }
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        & docker-compose up -d @Services
        return
    }

    throw "Docker Compose was not found, so missing dependencies cannot be started automatically."
}

function Ensure-BackendDependencies {
    param(
        [string]$Python,
        [string]$BackendPath
    )

    Push-Location $BackendPath
    try {
        & $Python -c "import alembic, fastapi, minio, qdrant_client" *> $null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Installing backend dependencies..."
            & $Python -m pip install -e .
        }
    } finally {
        Pop-Location
    }
}

function Resolve-NpmCommand {
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($npm) {
        return $npm.Source
    }

    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($npm) {
        return $npm.Source
    }

    $candidatePaths = @()
    if ($env:ProgramFiles) {
        $candidatePaths += Join-Path $env:ProgramFiles "nodejs\npm.cmd"
    }
    if (${env:ProgramFiles(x86)}) {
        $candidatePaths += Join-Path ${env:ProgramFiles(x86)} "nodejs\npm.cmd"
    }
    foreach ($path in $candidatePaths) {
        if ($path -and (Test-Path $path)) {
            return $path
        }
    }

    return $null
}

function Ensure-FrontendDependencies {
    param(
        [string]$NpmCommand,
        [string]$FrontendPath
    )

    $viteCommand = Join-Path $FrontendPath "node_modules\.bin\vite.cmd"
    if (Test-Path $viteCommand) {
        return
    }

    Write-Host "Installing frontend dependencies..."
    Push-Location $FrontendPath
    try {
        & $NpmCommand install
        if ($LASTEXITCODE -ne 0) {
            throw "npm install failed"
        }
    } finally {
        Pop-Location
    }

    if (-not (Test-Path $viteCommand)) {
        throw "Frontend dependencies installed, but Vite was still not found at $viteCommand"
    }
}

function Use-NodePath {
    param([string]$NpmCommand)

    $nodePath = Split-Path -Parent $NpmCommand
    if ($nodePath -and ($env:Path -notlike "*$nodePath*")) {
        $env:Path = "$nodePath;$env:Path"
    }
}

function Write-NodeInstallHelp {
    Write-Host "Node.js/npm is required to run the frontend, but npm was not found on PATH." -ForegroundColor Yellow
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "Install Node.js LTS with:"
        Write-Host "  winget install OpenJS.NodeJS.LTS"
    } else {
        Write-Host "Install Node.js LTS from https://nodejs.org, then open a new PowerShell window."
    }
    Write-Host "After installing Node.js, rerun:"
    Write-Host "  .\scripts\start-local.ps1"
    Write-Host "To run only the backend for now:"
    Write-Host "  .\scripts\start-local.ps1 -NoFrontend"
}

function Export-DotEnvToProcess {
    foreach ($key in $DotEnv.Keys) {
        if (-not [Environment]::GetEnvironmentVariable($key, "Process")) {
            Set-AppEnv $key $DotEnv[$key]
        }
    }
}

$databaseUrl = Get-DatabaseUrl
$databaseTarget = Get-DatabaseTarget $databaseUrl
$qdrantUrl = Get-QdrantUrl
$minioEndpoint = Get-MinioEndpoint
$minioBaseUrl = Get-MinioBaseUrl $minioEndpoint

$postgresFound = Test-TcpPort $databaseTarget.HostName $databaseTarget.Port
$qdrantFound = Test-HttpEndpoint "$qdrantUrl/collections"
$minioFound = Test-HttpEndpoint "$minioBaseUrl/minio/health/live"

Write-Host "Postgres: $(if ($postgresFound) { 'found' } else { 'missing' }) at $($databaseTarget.HostName):$($databaseTarget.Port)"
Write-Host "Qdrant:   $(if ($qdrantFound) { 'found' } else { 'missing' }) at $qdrantUrl"
Write-Host "MinIO:    $(if ($minioFound) { 'found' } else { 'missing' }) at $minioBaseUrl"

if ($CheckOnly) {
    if ($postgresFound -and $qdrantFound -and $minioFound) {
        exit 0
    }
    exit 1
}

$missingServices = @()
if (-not $postgresFound) { $missingServices += "postgres" }
if (-not $qdrantFound) { $missingServices += "qdrant" }
if (-not $minioFound) { $missingServices += "minio" }

Start-ComposeServices $missingServices

if (-not $postgresFound) {
    $databaseUrl = Get-ComposeDatabaseUrl
}
if (-not $qdrantFound) {
    $qdrantUrl = Get-ComposeQdrantUrl
}
if (-not $minioFound) {
    $minioEndpoint = "localhost:$(Get-Setting 'MINIO_API_PORT' '9000')"
}

Export-DotEnvToProcess
Set-AppEnv "DATABASE_URL" $databaseUrl
Set-AppEnv "QDRANT_URL" $qdrantUrl
Set-AppEnv "MINIO_ENDPOINT" $minioEndpoint
Set-AppEnv "MINIO_ACCESS_KEY" (Get-AliasedSetting @("MINIO_ACCESS_KEY", "MINIO_USER") "minioadmin")
Set-AppEnv "MINIO_SECRET_KEY" (Get-AliasedSetting @("MINIO_SECRET_KEY", "MINIO_PASSWORD") "minioadmin")
Set-AppEnv "MINIO_DATA_PATH" (Get-Setting "MINIO_DATA_PATH" ".mindmesh-data/minio")
Set-AppEnv "VITE_API_BASE_URL" (Get-Setting "VITE_API_BASE_URL" "")
Set-AppEnv "VITE_API_PROXY_TARGET" (Get-Setting "VITE_API_PROXY_TARGET" "http://127.0.0.1:8000")
Set-AppEnv "VITE_WORKSPACE_PIN" (Get-Setting "WORKSPACE_PIN" "")
Set-AppEnv "VITE_SINGLE_USER_EMAIL" (Get-Setting "SINGLE_USER_EMAIL" "local@mindmesh.app")
Set-AppEnv "VITE_SINGLE_USER_PASSWORD" (Get-Setting "SINGLE_USER_PASSWORD" "mindmesh-local-workspace-password")

if ($DepsOnly) {
    Write-Host "Dependencies are ready. Backend and frontend were not started because -DepsOnly was set."
    exit 0
}

$npmCommand = $null
if (-not $NoFrontend) {
    $npmCommand = Resolve-NpmCommand
    if (-not $npmCommand) {
        Write-NodeInstallHelp
        exit 1
    }
    Use-NodePath $npmCommand
}

if (-not $NoBackend) {
    $backendPath = Join-Path $RepoRoot "backend"
    $backendPort = [int](Get-Setting "BACKEND_PORT" "8000")
    $python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $python = "python"
    }

    if (Test-TcpPort "127.0.0.1" $backendPort) {
        Write-Host "Backend already appears to be running at http://127.0.0.1:$backendPort"
    } else {
        Ensure-BackendDependencies $python $backendPath

        Push-Location $backendPath
        try {
            Write-Host "Applying database migrations..."
            & $python -m alembic upgrade head
        } finally {
            Pop-Location
        }

        $backendCommand = "& '$python' -m uvicorn app.main:app --reload --host 127.0.0.1 --port $backendPort"
        Start-Process powershell -WorkingDirectory $backendPath -ArgumentList @("-NoExit", "-Command", $backendCommand)
        Write-Host "Backend starting at http://127.0.0.1:$backendPort"
    }

    Write-Host "Waiting for backend health..."
    if (-not (Wait-BackendHealth $backendPort)) {
        throw "Backend did not become healthy at http://127.0.0.1:$backendPort/health"
    }
    Write-Host "Backend is healthy."
}

if (-not $NoFrontend) {
    $frontendPath = Join-Path $RepoRoot "frontend"
    $frontendPort = [int](Get-Setting "FRONTEND_PORT" "8501")
    if (Test-TcpPort "127.0.0.1" $frontendPort) {
        Write-Host "Frontend already appears to be running at http://127.0.0.1:$frontendPort"
        exit 0
    }

    Ensure-FrontendDependencies $npmCommand $frontendPath

    $frontendCommand = "& '$npmCommand' run dev -- --host 127.0.0.1 --port $frontendPort"
    Start-Process powershell -WorkingDirectory $frontendPath -ArgumentList @("-NoExit", "-Command", $frontendCommand)
    Write-Host "Frontend starting at http://127.0.0.1:$frontendPort"
}
