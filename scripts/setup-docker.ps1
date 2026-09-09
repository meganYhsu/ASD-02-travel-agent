$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Repository root: $repoRoot" -ForegroundColor Cyan

$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Error "Docker CLI is not installed or not on PATH. Install Docker Desktop and reopen the terminal before running this script."
    exit 1
}

Write-Host "Checking Docker availability..." -ForegroundColor Yellow
try {
    docker info | Out-Null
} catch {
    Write-Error "Docker is not running. Start Docker Desktop and try again."
    exit 1
}

Write-Host "Pulling docker-compose configuration..." -ForegroundColor Yellow
try {
    docker compose config > $null
} catch {
    Write-Error "docker compose is not available. Ensure Docker Compose is enabled in Docker Desktop."
    exit 1
}

Write-Host "Stopping any existing containers..." -ForegroundColor Yellow
docker compose down --remove-orphans

Write-Host "Building and starting the application stack..." -ForegroundColor Yellow
docker compose up --build -d

Write-Host "Pulling required Ollama model..." -ForegroundColor Yellow
try {
    docker compose exec ollama ollama pull qwen2.5:3b
} catch {
    Write-Warning "The Ollama model pull did not complete automatically. Run the following manually if needed: docker compose exec ollama ollama pull qwen2.5:3b"
}

Write-Host "" 
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Open the following in a browser:" -ForegroundColor Cyan
Write-Host "  - Shared home: http://localhost:8080"
Write-Host "  - Student-5 frontend: http://localhost:8505"
Write-Host "  - Student-5 backend: http://localhost:5505"
Write-Host "  - Student-5 database: http://localhost:5405"
Write-Host "" 
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "  docker compose logs -f"
Write-Host "  docker compose down"
Write-Host "  docker compose exec ollama ollama pull qwen2.5:3b"
