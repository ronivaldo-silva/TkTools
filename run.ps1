# Define a política de execução para o processo atual para permitir a execução de scripts
Set-ExecutionPolicy Unrestricted -Scope Process -Force -ErrorAction SilentlyContinue

# Ativa o ambiente virtual
Write-Host "Ativando o ambiente virtual..." -ForegroundColor Cyan
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    .\.venv\Scripts\Activate.ps1
} elseif (Test-Path "..\.venv\Scripts\Activate.ps1") {
    ..\.venv\Scripts\Activate.ps1
} else {
    Write-Host "Aviso: Ambiente virtual (.venv) não encontrado!" -ForegroundColor Yellow
}

# Verifica se está na raiz do projeto e entra na pasta src, se necessário
if (Test-Path "src\main.py") {
    Set-Location -Path "src"
} elseif (-not (Test-Path "main.py")) {
    Write-Host "Erro: main.py não encontrado no diretório atual ou na subpasta src." -ForegroundColor Red
    exit
}

# Executa o aplicativo Flet
Write-Host "Iniciando o aplicativo TkTools na porta 8505..." -ForegroundColor Green
flet run main.py --w --port 8505
