[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$frontendDir = Join-Path $repoRoot 'apresentacao'

Set-Location $frontendDir

if (-not (Test-Path (Join-Path $frontendDir 'node_modules'))) {
    Write-Host 'Instalando dependências do frontend (npm ci) ...'
    npm ci
}

Write-Host 'Iniciando frontend (Vite) em http://localhost:5173 ...'
npm run dev
