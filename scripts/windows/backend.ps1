[CmdletBinding()]
param(
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot 'venv\Scripts\python.exe'

$pythonLauncher = (Get-Command py -ErrorAction SilentlyContinue)
if ($null -eq $pythonLauncher) {
    $pythonLauncher = (Get-Command python -ErrorAction SilentlyContinue)
}
if ($null -eq $pythonLauncher) {
    throw 'Não encontrei o comando `py` nem `python`. Instale o Python 3.11+ e garanta que está no PATH.'
}

if (-not (Test-Path $venvPython)) {
    Write-Host 'Criando virtualenv em .\venv ...'
    & $pythonLauncher.Source -m venv venv
}

Write-Host 'Instalando dependências do backend ...'
& $venvPython -m pip install -U pip
& $venvPython -m pip install -r (Join-Path $repoRoot 'requirements.txt')

$envFile = Join-Path $repoRoot '.env'
$envExample = Join-Path $repoRoot '.env.example'

if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    Write-Host 'Criando .env a partir de .env.example ...'
    Copy-Item $envExample $envFile
}

Write-Host "Iniciando API (Uvicorn) em http://127.0.0.1:$Port ..."
& $venvPython -m uvicorn functions.main:app --reload --host 127.0.0.1 --port $Port
