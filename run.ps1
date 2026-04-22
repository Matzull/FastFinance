# Script para ejecutar todos los servicios de FastFinance
# Uso: .\run.ps1

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                 🏦 FASTFINANCE                            ║" -ForegroundColor Cyan
Write-Host "║           Gestor de Finanzas Personales                   ║" -ForegroundColor Cyan
Write-Host "╠═══════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  Web:      http://127.0.0.1:8000                          ║" -ForegroundColor Cyan
Write-Host "║  API Docs: http://127.0.0.1:8000/docs                     ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Verificar configuración
Write-Host "🔍 Verificando configuración..." -ForegroundColor Yellow
Write-Host ""

$telegramEnabled = $false
if ($env:TELEGRAM_BOT_TOKEN) {
    Write-Host "✅ TELEGRAM_BOT_TOKEN configurado" -ForegroundColor Green
    $telegramEnabled = $true
} else {
    Write-Host "⚠️  TELEGRAM_BOT_TOKEN no configurado (bot deshabilitado)" -ForegroundColor Yellow
    Write-Host "   Para habilitar: `$env:TELEGRAM_BOT_TOKEN='tu_token'" -ForegroundColor Gray
}

if ($env:OPENAI_API_KEY) {
    Write-Host "✅ OPENAI_API_KEY configurado (OCR con Vision)" -ForegroundColor Green
} else {
    Write-Host "ℹ️  OPENAI_API_KEY no configurado (OCR usará PaddleOCR local)" -ForegroundColor Gray
}

Write-Host ""

# Lista de procesos a gestionar
$jobs = @()

try {
    # Iniciar servidor web
    Write-Host "🌐 Iniciando servidor web..." -ForegroundColor Cyan
    $webJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        uv run fastfinance-web 2>&1
    }
    $jobs += $webJob
    Write-Host "   Job ID: $($webJob.Id)" -ForegroundColor Gray

    # Esperar a que el servidor esté listo
    Start-Sleep -Seconds 3

    # Iniciar bot de Telegram si está configurado
    if ($telegramEnabled) {
        Write-Host "🤖 Iniciando bot de Telegram..." -ForegroundColor Cyan
        $botJob = Start-Job -ScriptBlock {
            Set-Location $using:PWD
            $env:TELEGRAM_BOT_TOKEN = $using:env:TELEGRAM_BOT_TOKEN
            $env:OPENAI_API_KEY = $using:env:OPENAI_API_KEY
            uv run fastfinance-bot 2>&1
        }
        $jobs += $botJob
        Write-Host "   Job ID: $($botJob.Id)" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "✅ Servicios iniciados correctamente" -ForegroundColor Green
    Write-Host "   Presiona Ctrl+C para detener todos los servicios" -ForegroundColor White
    Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""

    # Abrir navegador
    Start-Process "http://127.0.0.1:8000"

    # Monitorear los jobs
    while ($true) {
        foreach ($job in $jobs) {
            # Mostrar output nuevo
            $output = Receive-Job -Job $job -ErrorAction SilentlyContinue
            if ($output) {
                $output | ForEach-Object { Write-Host $_ }
            }
            
            # Verificar si el job terminó
            if ($job.State -eq "Completed" -or $job.State -eq "Failed") {
                Write-Host "⚠️  Job $($job.Id) terminó con estado: $($job.State)" -ForegroundColor Yellow
            }
        }
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host ""
    Write-Host "🛑 Deteniendo servicios..." -ForegroundColor Yellow
    
    foreach ($job in $jobs) {
        Write-Host "   Deteniendo Job $($job.Id)..." -ForegroundColor Gray
        Stop-Job -Job $job -ErrorAction SilentlyContinue
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
    }
    
    # También detener procesos uvicorn que puedan quedar
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*uvicorn*fastfinance*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Write-Host "✅ Todos los servicios detenidos" -ForegroundColor Green
}
